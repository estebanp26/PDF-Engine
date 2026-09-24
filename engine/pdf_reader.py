import hashlib
import io
import os
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Callable

import pymupdf as fitz

from engine.ocr_engine import FastOCREngine
from engine.search_index import normalize_text
from engine.telemetry import SpeedProfiler


def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    """Fast streaming SHA-256 of a file (used as the document cache key)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class PDFEngineReader:
    """Ultra-fast dual-stream PDF processor.

    - Digital text is always read directly from the text layer (no render).
    - A page is only sent to OCR when it has < ACTIVE_TEXT_CHARS useful chars.
    - Embedded images are OCR'd individually, but full-page scans never OCR
      their covering image twice (page render + image = 2x work).
    - Word-level coordinates are captured for digital text and OCR so the
      search engine can return and highlight exact match positions.
    - Results are cached by SHA-256 of the file.
    """

    ACTIVE_TEXT_CHARS = 30

    def __init__(self, ocr_workers: Optional[int] = None, cache_size: int = 3):
        self.ocr_engine = FastOCREngine(max_workers=ocr_workers)
        self._cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._cache_size = max(1, cache_size)

    # ------------------------------------------------------------------ cache
    def _cache_get(self, file_hash: str) -> Optional[Dict[str, Any]]:
        if file_hash in self._cache:
            self._cache.move_to_end(file_hash)
            return self._cache[file_hash]
        return None

    def _cache_put(self, file_hash: str, data: Dict[str, Any]) -> None:
        self._cache[file_hash] = data
        self._cache.move_to_end(file_hash)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    # ------------------------------------------------------------------- main
    def process_pdf(
        self,
        pdf_path: str,
        run_ocr_on_images: bool = True,
        dpi: int = 150,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Process a whole PDF.

        progress_cb receives a dict {stage, percent, ...} so callers can render
        live progress without a blocking spinner.
        """
        profiler = SpeedProfiler()
        file_hash = sha256_file(pdf_path)

        cached = self._cache_get(file_hash)
        if cached is not None:
            if progress_cb:
                progress_cb({"stage": "done", "percent": 100, "cache_hit": True,
                             "total_pages": cached["total_pages"]})
            cached["cached"] = True
            return cached

        def report(stage: str, percent: int, extra: Optional[Dict[str, Any]] = None):
            if progress_cb:
                payload = {"stage": stage, "percent": percent}
                if extra:
                    payload.update(extra)
                progress_cb(payload)

        report("parsing", 5)

        # ------------------------------------------------ pass 1: parse + list
        profiler.start_lap("pdf_open_and_parse")
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        pages_data: List[Dict[str, Any]] = []
        ocr_queue: List[tuple] = []          # (image_bytes, id)
        ocr_meta: Dict[str, Dict[str, Any]] = {}   # id -> mapping context

        # word-level coordinates for digital text: norm_word -> locations
        word_locations: Dict[str, List[Dict[str, Any]]] = {}

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1

            raw_text = page.get_text("text") or ""
            char_count = len(raw_text.strip())
            is_scanned = char_count < self.ACTIVE_TEXT_CHARS

            # Digital text word boxes (cheap C-level call)
            for word in page.get_text("words", sort=True):
                # word tuple: x0, y0, x1, y1, text, block, line, word_no
                w_text, x0, y0, x1, y1 = word[4], word[0], word[1], word[2], word[3]
                norm = normalize_text(w_text)
                if len(norm) < 2:
                    continue
                word_locations.setdefault(norm, []).append({
                    "page": page_num,
                    "src": "text",
                    "x0": round(x0, 2), "y0": round(y0, 2),
                    "x1": round(x1, 2), "y1": round(y1, 2),
                    "word": w_text,
                })

            # Embedded image detection
            image_list = page.get_images(full=True)
            page_images_info: List[Dict[str, Any]] = []
            image_rects: List[Dict[str, Any]] = []

            for img_index, img_meta in enumerate(image_list):
                xref = img_meta[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue
                if not base_image:
                    continue

                img_bytes = base_image["image"]
                img_ext = base_image["ext"]
                width = base_image["width"]
                height = base_image["height"]

                # Filter tiny icon decorations / logos
                if width < 40 or height < 40:
                    continue

                rects = page.get_image_rects(xref)
                rect = rects[0] if rects else None
                page_area = page.rect.width * page.rect.height
                cover = 0.0
                if rect is not None and page_area > 0:
                    cover = (rect.width * rect.height) / page_area

                img_id = f"p{page_num}_img{img_index+1}"
                page_images_info.append({
                    "id": img_id,
                    "page": page_num,
                    "width": width,
                    "height": height,
                    "format": img_ext,
                    "ocr_text": "",
                    "bytes": img_bytes,
                })
                image_rects.append({
                    "id": img_id,
                    "xref": xref,
                    "orig_w": width,
                    "orig_h": height,
                    "rect": (rect.x0, rect.y0, rect.x1, rect.y1) if rect else None,
                    "bytes": img_bytes,
                    "cover": cover,
                })

            # On scanned pages, if a single embedded image dominates the page
            # (>=50% coverage) OCR that image directly at native resolution
            # (skip the full-page render to avoid duplicated work). Otherwise a
            # scanned page is rendered for OCR; embedded images on pages with
            # real digital text are supplementary content and get their own OCR.
            dominant_scan = None
            if is_scanned and image_rects:
                best = max(image_rects, key=lambda r: r["cover"])
                if best["cover"] >= 0.5:
                    dominant_scan = best

            if run_ocr_on_images:
                if dominant_scan is not None:
                    info = dominant_scan
                    ocr_queue.append((info["bytes"], info["id"]))
                    ocr_meta[info["id"]] = {
                        "kind": "image",
                        "orig_w": info["orig_w"],
                        "orig_h": info["orig_h"],
                        "rect": info["rect"],
                        "cover": info["cover"],
                    }
                elif not is_scanned:
                    for info in image_rects:
                        ocr_queue.append((info["bytes"], info["id"]))
                        ocr_meta[info["id"]] = {
                            "kind": "image",
                            "orig_w": info["orig_w"],
                            "orig_h": info["orig_h"],
                            "rect": info["rect"],
                            "cover": info["cover"],
                        }

            if is_scanned and dominant_scan is None:
                # No good source image: render the whole page at target DPI.
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                rendered_bytes = pix.tobytes("png")
                scan_id = f"p{page_num}_full_scan"
                ocr_queue.append((rendered_bytes, scan_id))
                ocr_meta[scan_id] = {
                    "kind": "scan",
                    "dpi": dpi,
                    "zoom": zoom,
                }

            pages_data.append({
                "page": page_num,
                "text": raw_text.strip(),
                "is_scanned": is_scanned,
                "ocr_text": "",
                "images": page_images_info,
                "has_images": len(page_images_info) > 0,
            })

        profiler.end_lap("pdf_open_and_parse")
        report("parsing", 15, {"total_pages": total_pages})
        doc.close()

        # ------------------------------------------------ pass 2: parallel OCR
        profiler.start_lap("parallel_ocr")
        ocr_results_map: Dict[str, Dict[str, Any]] = {}
        if ocr_queue:
            batch_results = self.ocr_engine.process_batch(
                ocr_queue,
                progress_cb=lambda done, total: report(
                    "ocr",
                    15 + int(65 * done / total),
                    {"ocr_done": done, "ocr_total": total},
                ),
            )
            for res in batch_results:
                ocr_results_map[res["id"]] = res
        profiler.end_lap("parallel_ocr")

        report("indexing", 82)

        # ------------------------------------------------ pass 3: merge + index
        profiler.start_lap("indexing")
        for p in pages_data:
            page_num = p["page"]
            scan_id = f"p{page_num}_full_scan"
            scan_res = ocr_results_map.get(scan_id)
            if scan_res and scan_res["text"]:
                p["ocr_text"] = scan_res["text"]
                _register_ocr_boxes(word_locations, scan_id, page_num, "ocr", None,
                                    scan_res["boxes"], _map_scan_box_to_page,
                                    ocr_meta[scan_id])

            for img in p["images"]:
                img_res = ocr_results_map.get(img["id"])
                if img_res and img_res["text"]:
                    img["ocr_text"] = img_res["text"]
                    _register_ocr_boxes(word_locations, img["id"], page_num, "image_ocr",
                                        img["id"], img_res["boxes"], _map_image_box_to_page,
                                        ocr_meta.get(img["id"]))
        profiler.end_lap("indexing")

        report("finalizing", 95)

        # Build search index: word -> coordinates
        search_index = {
            "word_locations": word_locations,
            "pages_norm": {
                p["page"]: {
                    "text": normalize_text(p["text"]),
                    "ocr": normalize_text(p["ocr_text"]),
                    "images": [(img["id"], normalize_text(img["ocr_text"]))
                               for img in p["images"]],
                }
                for p in pages_data
            },
        }

        metrics = profiler.summary(total_pages=total_pages)

        result = {
            "file_path": pdf_path,
            "filename": os.path.basename(pdf_path),
            "total_pages": total_pages,
            "pages": pages_data,
            "ocr_items_processed": len(ocr_queue),
            "search_index": search_index,
            "cached": False,
            "metrics": metrics,
        }
        self._cache_put(file_hash, result)
        report("done", 100, {"total_pages": total_pages})
        return result


# ---------------------------------------------------------------------- helpers
def _map_scan_box_to_page(box, meta: Dict[str, Any]) -> List[float]:
    """Convert processed-pixel OCR box to PDF page points for a full-page scan."""
    zoom = meta.get("zoom", 150.0 / 72.0)
    return [box["x0"] / zoom, box["y0"] / zoom, box["x1"] / zoom, box["y1"] / zoom]


def _map_image_box_to_page(box, meta: Dict[str, Any]) -> List[float]:
    """Convert processed-pixel OCR box to PDF page points for an embedded image."""
    rect = meta.get("rect")
    if rect is None:
        return None
    rx0, ry0, rx1, ry1 = rect
    rw = rx1 - rx0
    rh = ry1 - ry0
    if not rw or not rh:
        return None
    x0 = rx0 + (box["x0"] / meta["orig_w"]) * rw
    y0 = ry0 + (box["y0"] / meta["orig_h"]) * rh
    x1 = rx0 + (box["x1"] / meta["orig_w"]) * rw
    y1 = ry0 + (box["y1"] / meta["orig_h"]) * rh
    return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]


def _register_ocr_boxes(word_locations, source_id, page, src_label, image_id, boxes, mapper, meta):
    """Add OCR word boxes into the shared word->coordinates index."""
    if not boxes:
        return
    for box in boxes:
        norm = normalize_text(box["text"])
        if len(norm) < 2:
            continue
        coords = mapper(box, meta)
        word_locations.setdefault(norm, []).append({
            "page": page,
            "src": src_label,
            "image_id": image_id,
            "x0": coords[0] if coords else None,
            "y0": coords[1] if coords else None,
            "x1": coords[2] if coords else None,
            "y1": coords[3] if coords else None,
            "word": box["text"],
        })