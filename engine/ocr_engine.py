import io
import os

# Isolate OpenMP threads to 1 per process to eliminate kernel CPU thread thrashing
# and multi-process lock contention when running parallel Tesseract workers.
os.environ["OMP_THREAD_LIMIT"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor

import pytesseract
import re
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw

# Tesseract standard optimization parameters for speed & Spanish/English recognition
TESSERACT_CONFIG = "--oem 1 --psm 3 -l spa+eng"

# Minimum word length stored in OCR box results (filters tesseract noise tokens)
MIN_WORD_LEN = 2


from engine.vocabulary_cleaner import vocab_cleaner


def clean_ocr_text(raw_text: str) -> str:
    """Clean common OCR noise, margin artifacts, and correct corrupted vocabulary."""
    return vocab_cleaner.clean_text_block(raw_text)


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

    # Only downscale truly huge pages (e.g. 3000+ px phone camera A4).
    # NEVER shrink narrow tickets/receipts (orig_w < 1000) where width is critical for font resolution!
    if max_dim > 2000 and orig_w >= 1000:
        ratio = 1800.0 / max_dim
        img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.BILINEAR)
    elif max_dim < 600 and min_dim > 50:
        ratio = 1000.0 / max_dim
        img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.BICUBIC)

    gray = ImageOps.grayscale(img)

    # Suppress outer 0.8% border scanner shadows
    gw, gh = gray.size
    bx = max(2, int(gw * 0.008))
    by = max(2, int(gh * 0.008))
    draw = ImageDraw.Draw(gray)
    draw.rectangle([0, 0, gw, by], fill=255)
    draw.rectangle([0, gh - by, gw, gh], fill=255)
    draw.rectangle([0, 0, bx, gh], fill=255)
    draw.rectangle([gw - bx, 0, gw, gh], fill=255)

    # Safe autocontrast with cutoff=0 preserves fine table text without clipping
    contrasted = ImageOps.autocontrast(gray, cutoff=0)

    # Gentle unsharp mask for clarity without noise amplification
    sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=2))

    sw, sh = sharpened.size
    return sharpened, (sw / orig_w if orig_w else 1.0), (sh / orig_h if orig_h else 1.0)


def _words_from_tesseract_data(data: Dict[str, Any], sx: float = 1.0, sy: float = 1.0) -> List[Dict[str, Any]]:
    """Flatten pytesseract.image_to_data output into per-word records (scaled back to native input px)."""
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
            "x0": int(round(left / sx)),
            "y0": int(round(top / sy)),
            "x1": int(round((left + w) / sx)),
            "y1": int(round((top + h) / sy)),
        })
    return boxes


def _init_ocr_worker():
    """Initializer for child processes in ProcessPoolExecutor."""
    os.environ["OMP_THREAD_LIMIT"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"


def ocr_single_image_worker(image_bytes: bytes, image_id: str = "") -> Dict[str, Any]:
    """Worker executed inside the process pool for parallel OCR.

    Uses image_to_data (single Tesseract pass) so we get both the recognized
    text and per-word boxes used to build the coordinate index.
    """
    _init_ocr_worker()
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            processed, sx, sy = preprocess_image_antitodo(pil_img)
            data = pytesseract.image_to_data(
                processed, config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT
            )
            boxes = _words_from_tesseract_data(data, sx, sy)

            # Reconstruct reading order using Tesseract's native (block, par, line) hierarchy
            lines: Dict[Tuple[int, int, int], List[str]] = {}
            for i in range(len(data.get("text", []))):
                w = (data.get("text") or [""])[i]
                w = (w or "").strip()
                if not w:
                    continue
                b_num = data.get("block_num", [0])[i]
                p_num = data.get("par_num", [0])[i]
                l_num = data.get("line_num", [0])[i]
                lines.setdefault((b_num, p_num, l_num), []).append(w)

            raw_text = "\n".join(" ".join(words) for _, words in sorted(lines.items())).strip()

            # Fast header watermark / logo inspection pass:
            # If the top of the image has content, perform local background subtraction
            # to recover faint or matrix-stippled logos/watermarks (e.g. "Previsalud Semedical")
            # that full-page layout segmentation drops as an isolated graphic.
            header_h = min(int(pil_img.height * 0.16), 380)
            if header_h >= 60:
                header_crop = pil_img.crop((0, max(0, int(pil_img.height * 0.012)), pil_img.width, header_h))
                gh = ImageOps.grayscale(header_crop)
                blurred_bg = gh.filter(ImageFilter.GaussianBlur(radius=8))
                diff = np.clip(255 - (np.array(blurred_bg, float) - np.array(gh, float)) * 3.5, 0, 255).astype(np.uint8)
                norm_header = Image.fromarray(diff)

                h_data = pytesseract.image_to_data(
                    norm_header, config="--oem 1 --psm 11 -l spa+eng", output_type=pytesseract.Output.DICT
                )
                h_words = []
                for idx in range(len(h_data.get("text", []))):
                    hw = (h_data.get("text") or [""])[idx].strip()
                    if len(hw) >= 3 and any(c.isalnum() for c in hw) and hw.lower() not in raw_text.lower():
                        cleaned_hw = vocab_cleaner.correct_word(hw)
                        h_words.append(cleaned_hw)
                        hl = int(h_data["left"][idx])
                        ht = int(h_data["top"][idx]) + int(pil_img.height * 0.012)
                        hw_box = int(h_data["width"][idx])
                        hh_box = int(h_data["height"][idx])
                        boxes.insert(0, {
                            "text": cleaned_hw,
                            "conf": float(h_data.get("conf", [80])[idx]),
                            "x0": hl, "y0": ht,
                            "x1": hl + hw_box, "y1": ht + hh_box,
                        })
                if h_words:
                    header_line = " ".join(h_words)
                    raw_text = header_line + "\n" + raw_text

            cleaned_text = clean_ocr_text(raw_text)

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
    """Multi-process parallel OCR engine with single-thread OpenMP isolation.

    By pinning each Tesseract worker to a single OpenMP thread (OMP_NUM_THREADS=1),
    we eliminate CPU core thrashing and context switching overhead. This allows
    near-linear scaling with available CPU cores.
    """

    def __init__(self, max_workers: Optional[int] = None):
        cpus = os.cpu_count() or 4
        # Allocate up to (cpus - 1) workers capped at 10, leaving CPU headroom for API/OS.
        self.max_workers = max_workers or min(10, max(1, cpus - 1))

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
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_ocr_worker) as executor:
            futures = [
                executor.submit(ocr_single_image_worker, img_bytes, img_id)
                for img_bytes, img_id in items
            ]
            for i, f in enumerate(futures, start=1):
                results.append(f.result())
                if progress_cb:
                    progress_cb(i, len(items))
        return results