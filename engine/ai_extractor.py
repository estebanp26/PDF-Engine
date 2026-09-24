import httpx
import json
import time
from typing import List, Dict, Any, Optional, Tuple

from engine.search_index import normalize_text, SearchEngine

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:1.5b"

# Qwen 2.5 is the single AI model of the system (per architecture decision)
FALLBACK_MODELS = ["qwen2.5:1.5b"]


class AIExtractor:
    """Structured value / answer extraction using local Qwen 2.5 via Ollama.

    Only relevant pruned context (< 600 tokens) is ever sent to the model;
    the lexical search engine handles keyword lookup, Qwen only interprets.
    """

    def __init__(self, ollama_url: str = OLLAMA_URL):
        self.ollama_url = ollama_url

    async def list_available_models(self) -> List[str]:
        """Fetch Qwen models available in local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.ollama_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m["name"] for m in data.get("models", [])]
                    qwen = [m for m in models if "qwen" in m.lower()]
                    return qwen or models[:1] or list(FALLBACK_MODELS)
        except Exception:
            pass
        return list(FALLBACK_MODELS)

    def build_pruned_context(
        self, document_data: Dict[str, Any], target_fields: List[str], max_chars: int = 3500
    ) -> Tuple[str, List[int]]:
        """Smart Context Pruning: only relevant pages/snippets reach the model."""
        pages = document_data.get("pages", [])
        if not pages:
            return "", []

        if len(pages) <= 3:
            all_text = []
            pages_used = []
            for p in pages:
                content = p.get("text", "") or p.get("ocr_text", "")
                if content:
                    all_text.append(f"--- PÁGINA {p['page']} ---\n{content}")
                    pages_used.append(p["page"])
            return "\n\n".join(all_text)[:max_chars], pages_used

        scores = []
        clean_fields = [normalize_text(f) for f in target_fields if f.strip()]

        for p in pages:
            combined = (p.get("text", "") + "\n" + p.get("ocr_text", ""))
            for img in p.get("images", []):
                combined += "\n" + img.get("ocr_text", "")

            norm_combined = normalize_text(combined)
            score = 0
            for f in clean_fields:
                if f in norm_combined:
                    score += 5
                for word in f.split():
                    if len(word) > 3 and word in norm_combined:
                        score += 1
            scores.append((score, p["page"], combined))

        scores.sort(key=lambda x: x[0], reverse=True)
        selected_snippets = []
        pages_used = []
        total_len = 0

        top_pages = scores[:4]
        top_page_nums = {x[1] for x in top_pages}
        if 1 not in top_page_nums and len(pages) > 0:
            top_pages.append((0, 1, pages[0].get("text", "") or pages[0].get("ocr_text", "")))

        top_pages.sort(key=lambda x: x[1])

        for score, page_num, text in top_pages:
            snippet = text.strip()
            if not snippet:
                continue
            chunk = f"--- PÁGINA {page_num} ---\n{snippet}\n"
            if total_len + len(chunk) > max_chars:
                chunk = chunk[:(max_chars - total_len)]
            selected_snippets.append(chunk)
            pages_used.append(page_num)
            total_len += len(chunk)
            if total_len >= max_chars:
                break

        return "\n".join(selected_snippets)[:max_chars], pages_used

    async def _generate(self, prompt: str, model: str = DEFAULT_MODEL) -> Tuple[Dict[str, Any], Optional[str]]:
        """Call Ollama /api/generate with JSON-only output. Returns (json, error)."""
        if not model:
            return {}, "No se especificó modelo."
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                res = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "keep_alive": "10m",
                        "options": {"temperature": 0.1, "num_predict": 120},
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    raw_response = data.get("response", "{}")
                    try:
                        return json.loads(raw_response), None
                    except json.JSONDecodeError:
                        clean_json = raw_response.strip()
                        if clean_json.startswith("```"):
                            clean_json = clean_json.split("\n", 1)[1]
                            clean_json = clean_json.rsplit("```", 1)[0]
                        try:
                            return json.loads(clean_json), None
                        except json.JSONDecodeError:
                            return {}, "El modelo devolvió JSON inválido."
                return {}, f"Ollama error {res.status_code}: {res.text}"
        except Exception as e:
            return {}, f"Error al conectar con el modelo IA: {str(e)}"

    # ------------------------------------------------------------- extraction
    async def extract_values(
        self,
        document_data: Dict[str, Any],
        target_fields: List[str],
        model: str = DEFAULT_MODEL,
    ) -> Dict[str, Any]:
        """Extract requested values with Qwen 2.5 from pruned context."""
        start_time = time.perf_counter()

        if not target_fields:
            return {"values": {}, "model_used": model, "latency_seconds": 0.0,
                    "latency_ms": 0.0, "pages_consulted": [], "error": None}

        context_text, pages_used = self.build_pruned_context(document_data, target_fields)
        fields_list_str = ", ".join([f'"{f.strip()}"' for f in target_fields if f.strip()])

        prompt = f"""Eres un extractor de datos de alta precisión y velocidad.
A continuación tienes extractos relevantes de un documento PDF:

{context_text}

TAREA:
Extrae exactamente los siguientes valores o campos solicitados:
{fields_list_str}

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE un objeto JSON válido. Sin explicaciones, sin markdown, sin texto adicional.
2. Si un campo no aparece en el texto, asígnale el valor "No encontrado".
3. Formato exacto:
{{
  "campo1": "valor encontrado",
  "campo2": "valor encontrado"
}}"""

        extracted_data, error_msg = await self._generate(prompt, model)
        if error_msg:
            extracted_data = {f: "No encontrado" for f in target_fields}

        elapsed = round(time.perf_counter() - start_time, 3)
        return {
            "values": extracted_data,
            "model_used": model,
            "latency_seconds": elapsed,
            "latency_ms": round(elapsed * 1000, 1),
            "pages_consulted": pages_used,
            "error": error_msg,
        }

    # ------------------------------------------------------------------- ask
    async def ask(
        self,
        document_data: Dict[str, Any],
        question: str,
        model: str = DEFAULT_MODEL,
        max_evidence_chars: int = 2500,
    ) -> Dict[str, Any]:
        """Answer a free-form question using search + Qwen (structured JSON).

        Flow: question -> lexical search for relevant snippets -> only those
        fragments go to Qwen -> structured {answer, unit, page, evidence,
        confidence}. Returns nulls with confidence 0 when no evidence exists.
        """
        start_time = time.perf_counter()

        if not question or not question.strip():
            return {"question": question, "answer": None, "unit": None, "page": None,
                    "evidence": None, "confidence": 0, "model_used": model,
                    "latency_ms": 0.0, "error": "Pregunta vacía."}

        search_res = SearchEngine.search(document_data, question)
        hits = search_res.get("results", [])

        # Build evidence from top hits (max 5, deduped by page+source)
        evidence_parts = []
        pages_used = []
        seen_pages: set = set()
        for h in hits:
            if len(evidence_parts) >= 5:
                break
            if h["page"] in seen_pages and len(seen_pages) >= 3:
                continue
            page_text = h["snippet"]
            header = f"[Página {h['page']} | {h['source_label']}]"
            evidence_parts.append(f"{header} {page_text}")
            pages_used.append(h["page"])
            seen_pages.add(h["page"])

        if not evidence_parts:
            return {"question": question, "answer": None, "unit": None, "page": None,
                    "evidence": None, "confidence": 0, "model_used": model,
                    "latency_ms": 0.0, "error": None,
                    "reason": "Sin evidencia relevante para la pregunta."}

        evidence = "\n".join(evidence_parts)[:max_evidence_chars]

        prompt = f"""Eres un asistente de extracción de datos de documentos.
PREGUNTA: {question}

EVIDENCIA EXTRAÍDA DEL DOCUMENTO (fragmentos relevantes):
{evidence}

RESPONDE ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
{{
  "answer": "respuesta corta basada en la evidencia",
  "unit": "unidad de medida si aplica, si no null",
  "page": número de página de la evidencia más relevante (o null),
  "evidence": "cita textual breve de la evidencia",
  "confidence": número entre 0 y 1
}}

REGLAS:
- NO inventes datos. Si la evidencia no contiene la respuesta, usa:
  {{"answer": null, "unit": null, "page": null, "evidence": null, "confidence": 0}}
- Sin explicaciones, sin markdown."""

        raw, error_msg = await self._generate(prompt, model)
        answer = raw.get("answer")
        confidence = raw.get("confidence")

        # Sanity: no invented answers without evidence
        if answer is None:
            confidence = 0
            evidence = None

        elapsed = round(time.perf_counter() - start_time, 3)
        return {
            "question": question,
            "answer": answer,
            "unit": raw.get("unit"),
            "page": raw.get("page"),
            "evidence": raw.get("evidence"),
            "confidence": round(float(confidence), 3) if confidence is not None else 0,
            "model_used": model,
            "latency_seconds": elapsed,
            "latency_ms": round(elapsed * 1000, 1),
            "pages_consulted": pages_used,
            "error": error_msg,
        }