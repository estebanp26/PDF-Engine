import os
import io
import shutil
import time
from typing import List, Optional
import pymupdf as fitz
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine
from engine.ai_extractor import AIExtractor
from engine.generator import PDFGenerator

app = FastAPI(title="PDF-Engine Enterprise", version="1.0.0")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Singleton reader & AI client
reader = PDFEngineReader()
ai_client = AIExtractor()

# In-memory store for active document
active_document = {
    "data": None,
    "doc_fitz": None,
    "file_path": None
}

class SearchRequest(BaseModel):
    query: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>PDF-Engine Enterprise</h1><p>Static files initializing...</p>"

@app.get("/api/system-status")
async def get_system_status():
    models = await ai_client.list_available_models()
    return {
        "status": "online",
        "cpu_cores": os.cpu_count() or 6,
        "ocr_engine": "Tesseract 5.x (Parallel 12-thread pool)",
        "available_models": models,
        "default_model": "qwen2.5:1.5b" if "qwen2.5:1.5b" in models else (models[0] if models else "none")
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), run_ocr: bool = True):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un documento PDF válido (.pdf)")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process with ultra-fast engine
    doc_data = reader.process_pdf(file_path, run_ocr_on_images=run_ocr)

    # Cache active document
    if active_document["doc_fitz"]:
        try:
            active_document["doc_fitz"].close()
        except Exception:
            pass

    active_document["data"] = doc_data
    active_document["file_path"] = file_path
    active_document["doc_fitz"] = fitz.open(file_path)

    # Create light serialized response (omit raw image bytes to keep payload fast)
    clean_pages = []
    for p in doc_data["pages"]:
        images_summary = []
        for img in p.get("images", []):
            images_summary.append({
                "id": img["id"],
                "page": img["page"],
                "width": img["width"],
                "height": img["height"],
                "format": img["format"],
                "ocr_text": img["ocr_text"]
            })
        clean_pages.append({
            "page": p["page"],
            "text": p["text"],
            "is_scanned": p["is_scanned"],
            "ocr_text": p["ocr_text"],
            "has_images": p["has_images"],
            "images": images_summary
        })

    return {
        "success": True,
        "filename": doc_data["filename"],
        "total_pages": doc_data["total_pages"],
        "ocr_items_processed": doc_data["ocr_items_processed"],
        "metrics": doc_data["metrics"],
        "pages": clean_pages
    }

@app.post("/api/load-sample")
async def load_sample_benchmark():
    sample_path = os.path.join(SAMPLES_DIR, "benchmark_20_pages.pdf")
    if not os.path.exists(sample_path):
        from test_benchmark import build_20_page_benchmark_pdf
        build_20_page_benchmark_pdf(sample_path)
    
    doc_data = reader.process_pdf(sample_path, run_ocr_on_images=True)

    if active_document["doc_fitz"]:
        try:
            active_document["doc_fitz"].close()
        except Exception:
            pass

    active_document["data"] = doc_data
    active_document["file_path"] = sample_path
    active_document["doc_fitz"] = fitz.open(sample_path)

    clean_pages = []
    for p in doc_data["pages"]:
        images_summary = []
        for img in p.get("images", []):
            images_summary.append({
                "id": img["id"],
                "page": img["page"],
                "width": img["width"],
                "height": img["height"],
                "format": img["format"],
                "ocr_text": img["ocr_text"]
            })
        clean_pages.append({
            "page": p["page"],
            "text": p["text"],
            "is_scanned": p["is_scanned"],
            "ocr_text": p["ocr_text"],
            "has_images": p["has_images"],
            "images": images_summary
        })

    return {
        "success": True,
        "filename": doc_data["filename"],
        "total_pages": doc_data["total_pages"],
        "ocr_items_processed": doc_data["ocr_items_processed"],
        "metrics": doc_data["metrics"],
        "pages": clean_pages
    }

class GeneratePDFRequest(BaseModel):
    pages: int = 20
    text_density: str = "repleta"
    images_count: int = 4
    degradation: str = "mixed_all"
    keywords: Optional[str] = "HABLAR, AHORA, CONFIDENCIAL_AUG, TOTAL_PAGAR"

@app.post("/api/generate-random-pdf")
async def generate_random_pdf(payload: GeneratePDFRequest):
    kw_list = [k.strip() for k in payload.keywords.split(",") if k.strip()] if payload.keywords else None
    
    result = PDFGenerator.generate(
        output_dir=SAMPLES_DIR,
        page_count=max(1, min(100, payload.pages)),
        text_density=payload.text_density,
        images_count=max(0, min(50, payload.images_count)),
        degradation=payload.degradation,
        keywords=kw_list
    )
    return result

class ScanGeneratedRequest(BaseModel):
    file_path: str

@app.post("/api/scan-generated-pdf")
async def scan_generated_pdf(payload: ScanGeneratedRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="El archivo PDF generado no existe en el servidor.")

    doc_data = reader.process_pdf(payload.file_path, run_ocr_on_images=True)

    if active_document["doc_fitz"]:
        try:
            active_document["doc_fitz"].close()
        except Exception:
            pass

    active_document["data"] = doc_data
    active_document["file_path"] = payload.file_path
    active_document["doc_fitz"] = fitz.open(payload.file_path)

    clean_pages = []
    for p in doc_data["pages"]:
        images_summary = []
        for img in p.get("images", []):
            images_summary.append({
                "id": img["id"],
                "page": img["page"],
                "width": img["width"],
                "height": img["height"],
                "format": img["format"],
                "ocr_text": img["ocr_text"]
            })
        clean_pages.append({
            "page": p["page"],
            "text": p["text"],
            "is_scanned": p["is_scanned"],
            "ocr_text": p["ocr_text"],
            "has_images": p["has_images"],
            "images": images_summary
        })

    return {
        "success": True,
        "filename": doc_data["filename"],
        "total_pages": doc_data["total_pages"],
        "ocr_items_processed": doc_data["ocr_items_processed"],
        "metrics": doc_data["metrics"],
        "pages": clean_pages
    }

@app.get("/api/download-generated/{filename}")
async def download_generated_pdf(filename: str):
    file_path = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

@app.post("/api/search")
async def search_keywords(payload: SearchRequest):
    if not active_document["data"]:
        raise HTTPException(status_code=400, detail="No hay ningún documento activo cargado.")
    
    t0 = time.perf_counter()
    results = SearchEngine.search(active_document["data"], payload.query)
    search_ms = round((time.perf_counter() - t0) * 1000, 2)
    results["search_latency_ms"] = search_ms
    return results

class AIRequest(BaseModel):
    fields: List[str]
    model: Optional[str] = "qwen2.5:1.5b"

@app.post("/api/extract-ai")
async def extract_ai_values(payload: AIRequest):
    if not active_document["data"]:
        raise HTTPException(status_code=400, detail="No hay ningún documento activo cargado.")

    result = await ai_client.extract_values(
        active_document["data"],
        target_fields=payload.fields,
        model=payload.model or "qwen2.5:1.5b"
    )
    return result

@app.get("/api/page-preview/{page_num}")
async def get_page_preview(page_num: int, highlight: Optional[str] = None):
    """Returns rendered page image at 120 DPI for high-clarity viewing with optional highlighted keywords."""
    if not active_document["doc_fitz"]:
        raise HTTPException(status_code=404, detail="No hay documento cargado.")
    
    doc = active_document["doc_fitz"]
    if page_num < 1 or page_num > len(doc):
        raise HTTPException(status_code=400, detail="Número de página fuera de rango.")

    page = doc[page_num - 1]
    
    # Apply visual highlighter on matching terms if requested
    added_annots = []
    if highlight and highlight.strip():
        import re
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
                rects = page.search_for(term)
                for r in rects:
                    annot = page.add_highlight_annot(r)
                    annot.set_colors(stroke=(1.0, 0.85, 0.0))  # Vivid yellow highlight
                    annot.update()
                    added_annots.append(annot)
            except Exception:
                pass

    pix = page.get_pixmap(dpi=120)
    img_bytes = pix.tobytes("png")

    # Clean up annotations so document remains unchanged
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
                fmt = img.get("format", "png").lower()
                media = f"image/{fmt}" if fmt in ["jpeg", "jpg", "png"] else "image/png"
                return Response(content=img["bytes"], media_type=media)
                
    raise HTTPException(status_code=404, detail="Imagen no encontrada.")
