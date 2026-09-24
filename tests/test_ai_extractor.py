import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from engine.ai_extractor import AIExtractor
from engine.search_index import SearchEngine

from tests.builders import make_digital_pdf
from engine.pdf_reader import PDFEngineReader


def _sample_doc(tmp_path, keywords=None):
    pdf = make_digital_pdf(str(tmp_path / "ai.pdf"), pages=4,
                           keywords=keywords or ["Proveedor: Acme SA", "NIT 900123456", "Monto: 2500000"])
    return PDFEngineReader().process_pdf(pdf, run_ocr_on_images=False)


def _answered_json():
    return {
        "answer": "2.500.000",
        "unit": "COP",
        "page": 1,
        "evidence": "Monto: 2500000",
        "confidence": 0.94,
    }


def _fake_generate(fn):
    """Monkeypatch AIExtractor._generate with an async fake."""
    def patch(monkeypatch):
        monkeypatch.setattr(AIExtractor, "_generate", fn)
    return patch


def test_extract_values_direct(monkeypatch, tmp_path):
    async def fake_generate(self, prompt, model):
        return {"campo1": "Acme SA", "campo2": "900123456"}, None
    monkeypatch.setattr(AIExtractor, "_generate", fake_generate)

    doc = _sample_doc(tmp_path)
    result = asyncio.run(AIExtractor().extract_values(doc, ["Proveedor", "NIT"]))
    assert result["values"]["campo1"] == "Acme SA"
    assert result["model_used"] == "qwen2.5:1.5b"
    assert result["pages_consulted"]  # pages actually pruned


def test_extract_values_error_fills_not_found(monkeypatch, tmp_path):
    async def fake_generate(self, prompt, model):
        return {}, "Ollama no disponible"
    monkeypatch.setattr(AIExtractor, "_generate", fake_generate)

    doc = _sample_doc(tmp_path)
    result = asyncio.run(AIExtractor().extract_values(doc, ["Proveedor"]))
    assert result["values"]["Proveedor"] == "No encontrado"
    assert result["error"]


def test_ask_with_evidence_structured(monkeypatch, tmp_path):
    async def fake_generate(self, prompt, model):
        return _answered_json(), None
    monkeypatch.setattr(AIExtractor, "_generate", fake_generate)

    doc = _sample_doc(tmp_path)
    result = asyncio.run(AIExtractor().ask(doc, "¿Cuál es el monto?"))
    assert result["answer"] == "2.500.000"
    assert result["page"] == 1
    assert result["confidence"] == 0.94
    assert result["evidence"]


def test_ask_without_evidence_no_invention(tmp_path):
    """No evidence -> nulls + confidence 0, even if model tried to invent."""
    doc = _sample_doc(tmp_path, keywords=["OTRO CONTENIDO DISTINTO v2"])
    result = asyncio.run(AIExtractor().ask(doc, "palabraquenoexisteXYZ"))
    assert result["answer"] is None
    assert result["page"] is None
    assert result["confidence"] == 0


def test_ask_invalid_json(monkeypatch, tmp_path):
    async def fake_generate(self, prompt, model):
        return {}, "El modelo devolvió JSON inválido."
    monkeypatch.setattr(AIExtractor, "_generate", fake_generate)

    doc = _sample_doc(tmp_path)
    result = asyncio.run(AIExtractor().ask(doc, "¿Cuál es el Monto?"))
    assert result["answer"] is None
    assert result["confidence"] == 0
    assert result["error"] is not None
    # con evidencia presente, el fallo del modelo → pregunta frustrada
    assert result["page"] is None


def test_empty_fields_not_sent_to_model(monkeypatch, tmp_path):
    called = {}

    async def fake_generate(self, prompt, model):
        called["hit"] = True
        return {}, None
    monkeypatch.setattr(AIExtractor, "_generate", fake_generate)

    doc = _sample_doc(tmp_path)
    result = asyncio.run(AIExtractor().extract_values(doc, []))
    assert "hit" not in called
    assert result["values"] == {}


def test_context_pruning_small():
    """Ensure pruned context stays bounded (< 600-ish tokens / ~3500 chars)."""
    ai = AIExtractor()
    pages = [
        {"page": i, "text": "Parrafo corporativo repetido con la palabra clave " * 20,
         "ocr_text": "factura" if i == 1 else "", "images": []}
        for i in range(1, 21)
    ]
    doc = {"pages": pages}
    ctx, used = ai.build_pruned_context(doc, ["FACTURA"], max_chars=3500)
    assert len(ctx) <= 3500
    assert used == sorted(used)