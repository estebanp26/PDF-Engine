import io
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PIL import Image

from engine.ocr_engine import (
    preprocess_image_antitodo,
    ocr_single_image_worker,
    FastOCREngine,
    TESSERACT_CONFIG,
)


TESSERACT_AVAILABLE = shutil.which("tesseract") is not None


def _make_image(size=(800, 600), color=(255, 255, 255)):
    img = Image.new("RGB", size, color=color)
    return img


def test_preprocess_returns_scales():
    img = _make_image()
    out, sx, sy = preprocess_image_antitodo(img)
    assert out.mode == "L" or out.mode == "RGB"
    assert 0 < sx <= 1.0 and 0 < sy <= 1.0


def test_preprocess_downscales_huge_image():
    img = _make_image(size=(4000, 3000))
    out, sx, sy = preprocess_image_antitodo(img)
    assert max(out.size) == 2000
    assert sx < 0.6 and sy < 0.6


def test_preprocess_upscales_small_image():
    img = _make_image(size=(300, 150))
    out, sx, sy = preprocess_image_antitodo(img)
    assert max(out.size) >= 600  # upscaled toward 1000px
    assert sx > 1.0


def test_ocr_worker_handles_garbage_bytes():
    res = ocr_single_image_worker(b"this is not an image", "x1")
    assert res["success"] is False
    assert res["text"] == ""


@pytest.mark.skipif(not TESSERACT_AVAILABLE, reason="Tesseract no está instalado en el sistema")
def test_ocr_worker_reads_text():
    from tests.builders import make_image_bytes
    res = ocr_single_image_worker(make_image_bytes(["HOLA MUNDO", "FACTURA 123"]), "img1")
    assert res["success"] is True
    assert res["length"] > 0
    assert "FACTURA" in res["text"].upper() or "123" in res["text"]


@pytest.mark.skipif(not TESSERACT_AVAILABLE, reason="Tesseract no está instalado en el sistema")
def test_ocr_batch_parallel(tmp_path):
    from tests.builders import make_image_bytes
    items = [(make_image_bytes([f"LINEA {i}"]), f"img{i}") for i in range(4)]
    engine = FastOCREngine(max_workers=2)
    progress = []
    results = engine.process_batch(items, progress_cb=lambda d, t: progress.append((d, t)))
    assert len(results) == 4
    assert progress[-1] == (4, 4)


def test_tesseract_config_uses_spanish():
    assert "spa" in TESSERACT_CONFIG and "eng" in TESSERACT_CONFIG