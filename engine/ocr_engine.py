import io
import os
import pytesseract
from PIL import Image, ImageOps, ImageFilter
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any, Tuple, Optional

# Tesseract standard optimization parameters for speed & Spanish/English recognition
TESSERACT_CONFIG = "--oem 1 --psm 3 -l spa+eng"

def preprocess_image_antitodo(img: Image.Image) -> Image.Image:
    """
    Robust 'Anti-Todo' preprocessing for poor quality, old, or low-contrast scans.
    1. Rescales to optimal OCR DPI range (approx 150-200 DPI equivalent).
    2. Converts to Grayscale.
    3. Auto-contrasts to strip yellow/gray backgrounds.
    4. Applies sharp contrast enhancement.
    """
    # 1. Normalize orientation & mode
    if img.mode != 'RGB' and img.mode != 'L':
        img = img.convert('RGB')
    
    # 2. Optimal dimension scaling for speed
    w, h = img.size
    max_dim = max(w, h)
    min_dim = min(w, h)
    
    # If image is excessively large, downsample to avoid CPU bottleneck (3x-4x speedup)
    if max_dim > 2200:
        ratio = 2000.0 / max_dim
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.BILINEAR)
    # If image is too small (e.g. cropped stamp/text snippet), upscale for character clarity
    elif max_dim < 600 and min_dim > 50:
        ratio = 1000.0 / max_dim
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.BICUBIC)

    # 3. Grayscale conversion
    gray = ImageOps.grayscale(img)

    # 4. Anti-todo Contrast Stretching: Cut off extreme 2% dark and light pixels
    contrasted = ImageOps.autocontrast(gray, cutoff=2)

    # 5. Mild sharpening to crisp up blurry or faded characters
    sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))

    return sharpened

def ocr_single_image_worker(image_bytes: bytes, image_id: str = "") -> Dict[str, Any]:
    """Worker function executed inside process pool for parallel OCR."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            processed = preprocess_image_antitodo(pil_img)
            text = pytesseract.image_to_string(processed, config=TESSERACT_CONFIG)
            cleaned_text = text.strip()
            return {
                "id": image_id,
                "text": cleaned_text,
                "length": len(cleaned_text),
                "success": True,
                "error": None
            }
    except Exception as e:
        return {
            "id": image_id,
            "text": "",
            "length": 0,
            "success": False,
            "error": str(e)
        }

class FastOCREngine:
    """Multi-process parallel OCR engine utilizing all CPU cores."""
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(12, os.cpu_count() or 4)

    def process_batch(self, items: List[Tuple[bytes, str]]) -> List[Dict[str, Any]]:
        """
        Process a list of (image_bytes, image_id) tuples in parallel.
        Returns a list of result dictionaries.
        """
        if not items:
            return []
        
        # If single item, run directly to save fork overhead
        if len(items) == 1:
            return [ocr_single_image_worker(items[0][0], items[0][1])]

        workers = min(self.max_workers, len(items))
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(ocr_single_image_worker, img_bytes, img_id)
                for img_bytes, img_id in items
            ]
            results = [f.result() for f in futures]
        return results
