import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from tests.builders import (
    make_digital_pdf,
    make_scanned_pdf,
    make_corrupt_pdf,
)

from engine.pdf_reader import PDFEngineReader


def test_valid_digital_pdf(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "digital.pdf"), pages=5)
    doc = PDFEngineReader().process_pdf(pdf, run_ocr_on_images=False)
    assert doc["total_pages"] == 5
    # all pages digital, text extracted, OCR queue empty
    assert doc["ocr_items_processed"] == 0
    assert all(p["is_scanned"] is False for p in doc["pages"])
    assert any("NIT" in p["text"] for p in doc["pages"])
    assert doc["cached"] is False


def test_corrupt_pdf_raises(tmp_path):
    pdf = make_corrupt_pdf(str(tmp_path / "malo.pdf"))
    with pytest.raises(Exception):
        PDFEngineReader().process_pdf(pdf, run_ocr_on_images=False)


def test_scanned_pdf_not_double_ocr(tmp_path):
    """Full-page scan image must be OCR'd once (dedup), not twice."""
    pdf = make_scanned_pdf(str(tmp_path / "scan.pdf"), pages=2)
    reader = PDFEngineReader()
    doc = reader.process_pdf(pdf, run_ocr_on_images=True)
    assert doc["total_pages"] == 2
    # 1 OCR item per scanned page (the page render), not 2 (page + covering image)
    assert doc["ocr_items_processed"] == 2
    assert all(p["is_scanned"] for p in doc["pages"])


def test_cache_hit_and_miss(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "cache.pdf"), pages=3)
    reader = PDFEngineReader()
    first = reader.process_pdf(pdf, run_ocr_on_images=False)
    assert first["cached"] is False
    second = reader.process_pdf(pdf, run_ocr_on_images=False)
    assert second["cached"] is True
    assert second is first


def test_cache_miss_for_different_file(tmp_path):
    a = make_digital_pdf(str(tmp_path / "a.pdf"), pages=3)
    b = make_digital_pdf(str(tmp_path / "b.pdf"), pages=3)
    reader = PDFEngineReader()
    r1 = reader.process_pdf(a, run_ocr_on_images=False)
    r2 = reader.process_pdf(b, run_ocr_on_images=False)
    assert r1["cached"] is False and r2["cached"] is False


def test_digital_pages_not_ocr_rendered(tmp_path):
    """Pages with enough digital text must NOT be rendered for OCR."""
    pdf = make_digital_pdf(str(tmp_path / "no_ocr.pdf"), pages=5)
    doc = PDFEngineReader().process_pdf(pdf, run_ocr_on_images=True)
    assert doc["ocr_items_processed"] == 0