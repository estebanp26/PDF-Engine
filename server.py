import asyncio
import json
import os
import re
import shutil
import time
import uuid
from typing import List, Optional

import pymupdf as fitz
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine
from engine.ai_extractor import AIExtractor, DEFAULT_MODEL

app = FastAPI(title="PDF-Engine Enterprise", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

if os.path.exists(os.path.join(FRONTEND_DIST, "assets")):
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

# Limits / security
MAX_UPLOAD_MB = 50
MAX_PAGES = 300
ALLOWED_EXT = {".pdf"}

# Singleton engine
reader = PDFEngineReader()
ai_client = AIExtractor()

# In-memory store for the active document
active_document = {"data": None, "doc_fitz": None, "file_path": None}

# Async jobs for long processing (progress + result polling)
jobs: dict = {}


class SearchRequest(BaseModel):
    query: str


class AIRequest(BaseModel):
    fields: List[str]
    model: Optional[str] = DEFAULT_MODEL


class AskRequest(BaseModel):
    question: str
    model: Optional[str] = DEFAULT_MODEL


# ---------------------------------------------------------------- validators
def _validate_pdf_file(file_path: str) -> int:
    """Return page count or raise HTTPException for invalid/oversized PDFs."""
    try:
        with fitz.open(file_path) as doc:
            n = len(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF corrupto o inválido: {str(e)}")
    if n > MAX_PAGES:
        raise HTTPException(status_code=400, detail=f"PDF supera el límite de {MAX_PAGES} páginas.")
    return n


def _light_payload(doc_data: dict) -> dict:
    """Lightweight serialized response (omits raw image bytes & search index)."""
    pages = doc_data.get("pages", [])
    digital = sum(1 for p in pages if not p["is_scanned"])
    ocr = len(pages) - digital
    clean_pages = []
    for p in pages:
        images_summary = []
        for img in p.get("images", []):
            images_summary.append({
                "id": img["id"], "page": img["page"], "width": img["width"],
                "height": img["height"], "format": img["format"], "ocr_text": img["ocr_text"],
            })
        clean_pages.append({
            "page": p["page"], "text": p["text"], "is_scanned": p["is_scanned"],
            "ocr_text": p["ocr_text"], "has_images": p["has_images"], "images": images_summary,
        })
    return {
        "success": True,
        "filename": doc_data["filename"],
        "total_pages": doc_data["total_pages"],
        "digital_pages": digital,
        "ocr_pages": ocr,
        "ocr_items_processed": doc_data.get("ocr_items_processed", 0),
        "cached": doc_data.get("cached", False),
        "metrics": doc_data.get("metrics", {}),
        "pages": clean_pages,
    }


# ---------------------------------------------------------------- job runner
def _setup_job(process_fn) -> str:
    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {"status": "running", "progress": {}, "document": None, "error": None}

    def progress_cb(payload: dict):
        jobs[job_id]["progress"] = payload

    async def run():
        try:
            doc_data = await asyncio.to_thread(process_fn, progress_cb)
            _activate_document(doc_data)
            jobs[job_id]["document"] = _light_payload(doc_data)
            jobs[job_id]["status"] = "done"
        except HTTPException as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e.detail)
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"Error interno: {str(e)}"

    asyncio.get_event_loop().create_task(run())
    return job_id


def _activate_document(doc_data: dict):
    global active_document
    if active_document["doc_fitz"]:
        try:
            active_document["doc_fitz"].close()
        except Exception:
            pass
    file_path = doc_data.get("file_path")
    active_document["data"] = doc_data
    active_document["file_path"] = file_path
    try:
        active_document["doc_fitz"] = fitz.open(file_path)
    except Exception:
        active_document["doc_fitz"] = None


def _process_and_activate(file_path: str, run_ocr: bool, progress_cb):
    return reader.process_pdf(file_path, run_ocr_on_images=run_ocr, progress_cb=progress_cb)


# -------------------------------------------------------------------- routes
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    react_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(react_index):
        with open(react_index, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>PDF-Engine Enterprise</h1><p>Frontend no compilado. Ejecuta: cd frontend && npm run build</p>"


@app.get("/api/system-status")
async def get_system_status():
    models = await ai_client.list_available_models()
    default_model = models[0] if models else DEFAULT_MODEL
    return {
        "status": "online",
        "cpu_cores": os.cpu_count() or 6,
        "ocr_engine": f"Tesseract 5.x (pool ~{(os.cpu_count() or 4 + 1) // 2} workers)",
        "ai_engine": "Qwen 2.5 via Ollama",
        "available_models": models,
        "default_model": default_model,
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), run_ocr: bool = Form(True)):
    filename = os.path.basename(file.filename or "documento.pdf")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="El archivo debe ser un documento PDF válido (.pdf).")

    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}_{filename}")
    size = 0
    with open(file_path, "wb") as buffer:
        while True:
            chunk = file.file.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                buffer.close()
                os.remove(file_path)
                raise HTTPException(status_code=400, detail=f"El archivo supera el límite de {MAX_UPLOAD_MB} MB.")
            buffer.write(chunk)

    _validate_pdf_file(file_path)
    job_id = _setup_job(
        lambda cb: _process_and_activate(file_path, run_ocr and True, cb)
    )
    return {"job_id": job_id, "status": "running"}


@app.post("/api/load-sample")
async def load_sample_benchmark():
    sample_path = os.path.join(SAMPLES_DIR, "benchmark_20_pages.pdf")
    if not os.path.exists(sample_path):
        from test_benchmark import build_20_page_benchmark_pdf
        build_20_page_benchmark_pdf(sample_path)
    _validate_pdf_file(sample_path)
    job_id = _setup_job(lambda cb: _process_and_activate(sample_path, True, cb))
    return {"job_id": job_id, "status": "running"}


@app.get("/api/progress/{job_id}")
async def get_job_progress(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado.")
    return {"job_id": job_id, "status": job["status"], "progress": job["progress"]}


@app.get("/api/document/{job_id}")
async def get_job_document(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado.")
    if job["status"] == "error":
        raise HTTPException(status_code=500, detail=job["error"])
    if job["status"] != "done" or not job["document"]:
        raise HTTPException(status_code=202, detail="Procesamiento aún en curso.")
    return job["document"]


@app.post("/api/search")
async def search_keywords(payload: SearchRequest):
    if not active_document["data"]:
        raise HTTPException(status_code=400, detail="No hay ningún documento activo cargado.")

    t0 = time.perf_counter()
    results = SearchEngine.search(active_document["data"], payload.query)
    results["search_latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return results


@app.post("/api/extract-ai")
async def extract_ai_values(payload: AIRequest):
    if not active_document["data"]:
        raise HTTPException(status_code=400, detail="No hay ningún documento activo cargado.")

    result = await ai_client.extract_values(
        active_document["data"],
        target_fields=payload.fields,
        model=payload.model or DEFAULT_MODEL,
    )
    return result


@app.post("/api/ask")
async def ask_question(payload: AskRequest):
    """Question-answering: lexical search for evidence + Qwen 2.5 interpretation."""
    if not active_document["data"]:
        raise HTTPException(status_code=400, detail="No hay ningún documento activo cargado.")

    result = await ai_client.ask(
        active_document["data"],
        question=payload.question,
        model=payload.model or DEFAULT_MODEL,
    )
    return result


@app.get("/api/page-preview/{page_num}")
async def get_page_preview(page_num: int, highlight: Optional[str] = None, rects: Optional[str] = None):
    """Rendered page at 120 DPI with optional keyword/highlight boxes."""
    if not active_document["doc_fitz"]:
        raise HTTPException(status_code=404, detail="No hay documento cargado.")

    doc = active_document["doc_fitz"]
    if page_num < 1 or page_num > len(doc):
        raise HTTPException(status_code=400, detail="Número de página fuera de rango.")

    page = doc[page_num - 1]
    added_annots = []

    # 1) Explicit coordinate boxes (from the search engine)
    if rects:
        try:
            boxes = json.loads(rects)
            for box in boxes:
                if len(box) == 4:
                    annot = page.add_highlight_annot(fitz.Rect(*box))
                    annot.set_colors(stroke=(1.0, 0.85, 0.0))
                    annot.update()
                    added_annots.append(annot)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # 2) Text-layer search highlight (digital text only)
    if highlight and highlight.strip():
        clean_hl = highlight.strip()
        tokens = [w for w in re.split(r'[\s,\-_:\.;/]+', clean_hl) if len(w) >= 2]
        search_terms = []
        if len(tokens) > 1:
            search_terms.append(clean_hl)
        for t in tokens:
            if t not in search_terms:
                search_terms.append(t)

        for term in search_terms:
            try:
                for r in page.search_for(term):
                    annot = page.add_highlight_annot(r)
                    annot.set_colors(stroke=(1.0, 0.85, 0.0))
                    annot.update()
                    added_annots.append(annot)
            except Exception:
                pass

    pix = page.get_pixmap(dpi=120)
    img_bytes = pix.tobytes("png")

    for annot in added_annots:
        try:
            page.delete_annot(annot)
        except Exception:
            pass

    return Response(content=img_bytes, media_type="image/png")


@app.get("/api/extracted-image/{image_id}")
async def get_extracted_image(image_id: str):
    """Serves raw bytes of an extracted embedded image."""
    if not active_document["data"]:
        raise HTTPException(status_code=404, detail="No hay documento cargado.")

    for p in active_document["data"].get("pages", []):
        for img in p.get("images", []):
            if img["id"] == image_id and "bytes" in img:
                fmt = str(img.get("format", "png")).lower()
                media = f"image/{fmt}" if fmt in ["jpeg", "jpg", "png"] else "image/png"
                return Response(content=img["bytes"], media_type=media)

    raise HTTPException(status_code=404, detail="Imagen no encontrada.")