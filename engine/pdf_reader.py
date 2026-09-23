import fitz  # PyMuPDF
import io
import os
from typing import List, Dict, Any, Optional
from engine.ocr_engine import FastOCREngine
from engine.telemetry import SpeedProfiler

class PDFEngineReader:
    """Ultra-fast dual-stream PDF processor for 20+ page documents."""
    
    def __init__(self, ocr_workers: Optional[int] = None):
        self.ocr_engine = FastOCREngine(max_workers=ocr_workers)

    def process_pdf(self, pdf_path: str, run_ocr_on_images: bool = True) -> Dict[str, Any]:
        """
        Processes entire PDF (20+ pages) in record time:
        1. Fast digital text stream extraction (C-level).
        2. Direct binary extraction of embedded images.
        3. Parallel OCR on scanned pages and text-bearing images.
        4. Metrics computation.
        """
        profiler = SpeedProfiler()
        profiler.start_lap("pdf_open_and_parse")

        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        pages_data: List[Dict[str, Any]] = []
        ocr_queue: List[tuple] = []  # List of (image_bytes, identifier)

        # 1. First Pass: Fast C-level page traversal
        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1

            # Extract native text
            raw_text = page.get_text("text") or ""
            char_count = len(raw_text.strip())

            # Detect embedded images
            image_list = page.get_images(full=True)
            page_images_info = []

            for img_index, img_meta in enumerate(image_list):
                xref = img_meta[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                img_bytes = base_image["image"]
                img_ext = base_image["ext"]
                width = base_image["width"]
                height = base_image["height"]

                # Filter out tiny icon decorations (< 40x40 px)
                if width < 40 or height < 40:
                    continue

                img_id = f"p{page_num}_img{img_index+1}"
                page_images_info.append({
                    "id": img_id,
                    "page": page_num,
                    "width": width,
                    "height": height,
                    "format": img_ext,
                    "ocr_text": "",
                    "bytes": img_bytes
                })

                # Queue image for OCR if enabled
                if run_ocr_on_images:
                    ocr_queue.append((img_bytes, img_id))

            # Check if page is a pure scan / image-only (less than 30 characters of digital text)
            is_scanned = (char_count < 30)

            if is_scanned:
                # Render page at 150 DPI for OCR (optimal speed/accuracy sweet spot)
                zoom = 150.0 / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                rendered_bytes = pix.tobytes("png")
                
                scan_id = f"p{page_num}_full_scan"
                ocr_queue.append((rendered_bytes, scan_id))

            pages_data.append({
                "page": page_num,
                "text": raw_text.strip(),
                "is_scanned": is_scanned,
                "ocr_text": "",
                "images": page_images_info,
                "has_images": len(page_images_info) > 0
            })

        profiler.end_lap("pdf_open_and_parse")

        # 2. Second Pass: Parallel OCR (12 CPU threads)
        profiler.start_lap("parallel_ocr")
        ocr_results_map = {}
        if ocr_queue:
            batch_results = self.ocr_engine.process_batch(ocr_queue)
            for res in batch_results:
                ocr_results_map[res["id"]] = res["text"]
        profiler.end_lap("parallel_ocr")

        # 3. Third Pass: Merge OCR results back into page data
        for p in pages_data:
            page_num = p["page"]
            scan_id = f"p{page_num}_full_scan"
            if scan_id in ocr_results_map and ocr_results_map[scan_id]:
                p["ocr_text"] = ocr_results_map[scan_id]

            # Merge image OCR text
            for img in p["images"]:
                img_id = img["id"]
                if img_id in ocr_results_map:
                    img["ocr_text"] = ocr_results_map[img_id]

        doc.close()

        # Build final metrics
        metrics = profiler.summary(total_pages=total_pages)

        return {
            "file_path": pdf_path,
            "filename": os.path.basename(pdf_path),
            "total_pages": total_pages,
            "pages": pages_data,
            "ocr_items_processed": len(ocr_queue),
            "metrics": metrics
        }
