import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.builders import make_digital_pdf, make_mixed_pdf
from engine.pdf_reader import PDFEngineReader
from engine.search_index import SearchEngine, normalize_text


def _doc_text(pdf_path, run_ocr=False):
    return PDFEngineReader().process_pdf(pdf_path, run_ocr_on_images=run_ocr)


def test_normalize_text():
    assert normalize_text("Administración") == "administracion"
    assert normalize_text("ADMINISTRACION") == "administracion"
    assert normalize_text("") == ""


def test_exact_match_with_coords(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "s.pdf"), pages=3)
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "NIT")
    assert res["total_matches"] >= 3
    assert res["matched_pages"] == [1, 2, 3]
    first = res["results"][0]
    assert first["page"] >= 1
    assert first["x0"] is not None and first["y0"] is not None
    assert first["x1"] is not None and first["y1"] is not None


def test_case_insensitive(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "ci.pdf"), pages=2)
    doc = _doc_text(pdf)
    for q in ("FACTURA", "factura", "Factura"):
        assert SearchEngine.search(doc, q)["total_matches"] >= 2


def test_accent_insensitive(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "acc.pdf"), pages=1, keywords=["ADMINISTRACIÓN PÚBLICA"])
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "administracion")
    assert res["total_matches"] >= 1


def test_exact_priority_over_fuzzy(tmp_path):
    """A clean exact match must be returned as 'exacto', not fuzzy."""
    pdf = make_digital_pdf(str(tmp_path / "ex.pdf"), pages=2)
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "NIT")
    assert all(r["match_type"] == "exacto" for r in res["results"])


def test_no_match_returns_empty(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "nomatch.pdf"), pages=2)
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "zzznoexistekey")
    assert res["total_matches"] == 0 and res["results"] == []


def test_phrase_multitoken(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "phrase.pdf"), pages=4)
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "NIT auditoria")
    assert res["total_matches"] >= 1
    # phrase results keep the query as token_searched
    assert any(r["token_searched"] == "NIT auditoria" for r in res["results"])


def test_multi_page_results(tmp_path):
    pdf = make_digital_pdf(str(tmp_path / "multi.pdf"), pages=6)
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "FACTURA")
    assert len(res["matched_pages"]) == 6


def test_mixed_image_document(tmp_path):
    pdf = make_mixed_pdf(str(tmp_path / "mixed.pdf"))
    doc = _doc_text(pdf, run_ocr=False)
    # digital keyword searchable
    res = SearchEngine.search(doc, "NIT_999_TEST")
    assert res["total_matches"] >= 1


def test_prefix_search_incomplete_word(tmp_path):
    """Searching for 'doc' must match words like 'DOCUMENTO' or 'doctor'."""
    pdf = make_digital_pdf(str(tmp_path / "prefix.pdf"), pages=2, keywords=["DOCUMENTO", "DOCTOR"])
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "doc")
    assert res["total_matches"] >= 2
    assert any(r["match_type"] == "prefijo" and "doc" in r["matched_term"].lower() for r in res["results"])


def test_substring_search(tmp_path):
    """Searching for internal substring 'operacion' matches 'OPERACIONES'."""
    pdf = make_digital_pdf(str(tmp_path / "sub.pdf"), pages=2, keywords=["OPERACIONES"])
    doc = _doc_text(pdf)
    res = SearchEngine.search(doc, "operacion")
    assert res["total_matches"] >= 2
    assert any("operacion" in r["matched_term"].lower() for r in res["results"])