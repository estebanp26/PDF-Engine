import io
import os
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor

import pytesseract
from PIL import Image, ImageOps, ImageFilter

# Tesseract standard optimization parameters for speed & Spanish/English recognition
TESSERACT_CONFIG = "--oem 1 --psm 3 -l spa+eng"

# Minimum word length stored in OCR box results (filters tesseract noise tokens)
MIN_WORD_LEN = 2


def preprocess_image_antitodo(img: Image.Image) -> Tuple[Image.Image, float, float]:
    """
    Adaptive 'Anti-Todo' preprocessing.

    Returns (processed_image, scale_x, scale_y) where scale_x/y maps original
    pixel coordinates back into the processed image coordinate space. This
    allows downstream callers (word-box mapping) to convert OCR pixel boxes
    into PDF page coordinates.

    Only expensive resizing kicks in when the image is genuinely too large
    or too small; typical scans pass through unchanged.
    """
    orig_w, orig_h = img.size

    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    max_dim = max(orig_w, orig_h)
    min_dim = min(orig_w, orig_h)

    if max_dim > 2200:
        ratio = 2000.0 / max_dim
        img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.BILINEAR)
    elif max_dim < 600 and min_dim > 50:
        ratio = 1000.0 / max_dim
        img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.BICUBIC)

    gray = ImageOps.grayscale(img)

    # Auto-contrast is cheap and effective for yellow/dark backgrounds
    contrasted = ImageOps.autocontrast(gray, cutoff=2)

    # Mild sharpening for faded scans; only ~1ms for 2000px images
    sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))

    sw, sh = sharpened.size
    return sharpened, (sw / orig_w if orig_w else 1.0), (sh / orig_h if orig_h else 1.0)


def _words_from_tesseract_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten pytesseract.image_to_data output into per-word records (processed px)."""
    boxes: List[Dict[str, Any]] = []
    n = len(data.get("text", []))
    for i in range(n):
        word = (data.get("text") or [""])[i]
        word = (word or "").strip()
        if len(word) < MIN_WORD_LEN:
            continue
        try:
            conf = float(data["conf"][i])
        except (KeyError, ValueError, TypeError):
            conf = -1.0
        left = int(data["left"][i])
        top = int(data["top"][i])
        w = int(data["width"][i])
        h = int(data["height"][i])
        if w <= 0 or h <= 0:
            continue
        boxes.append({
            "text": word,
            "conf": conf,
            "x0": left,
            "y0": top,
            "x1": left + w,
            "y1": top + h,
        })
    return boxes


def ocr_single_image_worker(image_bytes: bytes, image_id: str = "") -> Dict[str, Any]:
    """Worker executed inside the process pool for parallel OCR.

    Uses image_to_data (single Tesseract pass) so we get both the recognized
    text and per-word boxes used to build the coordinate index.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            processed, _, _ = preprocess_image_antitodo(pil_img)
            data = pytesseract.image_to_data(
                processed, config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT
            )
            boxes = _words_from_tesseract_data(data)

            # Reconstruct paragraphs/line text from box order
            lines: Dict[int, List[Tuple[int, str]]] = {}
            for b in boxes:
                row = int(b["y0"] // 12)
                lines.setdefault(row, []).append((b["x0"], b["text"]))
            text = ""
            for row in sorted(lines):
                ordered = [w for _, w in sorted(lines[row], key=lambda t: t[0])]
                text += " ".join(ordered) + "\n"
            cleaned_text = text.strip()

            return {
                "id": image_id,
                "text": cleaned_text,
                "length": len(cleaned_text),
                "boxes": boxes,
                "success": True,
                "error": None,
            }
    except Exception as e:
        return {
            "id": image_id,
            "text": "",
            "length": 0,
            "boxes": [],
            "success": False,
            "error": str(e),
        }


class FastOCREngine:
    """Multi-process parallel OCR engine with configurable worker count.

    NOTE: Tesseract internally uses OpenMP threads too, so throwing every CPU
    core at it rarely helps. The default (~2 workers per physical core budget)
    is a sane starting point; tune with benchmark_ocr_tuning.py.
    """

    def __init__(self, max_workers: Optional[int] = None):
        cpus = os.cpu_count() or 4
        self.max_workers = max_workers or min(12, max(1, (cpus + 1) // 2))

    def process_batch(
        self,
        items: List[Tuple[bytes, str]],
        progress_cb=None,
    ) -> List[Dict[str, Any]]:
        """
        Process a list of (image_bytes, image_id) tuples in parallel.

        progress_cb(completed: int, total: int) is invoked after each item.
        """
        if not items:
            return []

        if len(items) == 1:
            results = [ocr_single_image_worker(items[0][0], items[0][1])]
            if progress_cb:
                progress_cb(1, 1)
            return results

        workers = min(self.max_workers, len(items))
        results: List[Dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(ocr_single_image_worker, img_bytes, img_id)
                for img_bytes, img_id in items
            ]
            for i, f in enumerate(futures, start=1):
                results.append(f.result())
                if progress_cb:
                    progress_cb(i, len(items))
        return results