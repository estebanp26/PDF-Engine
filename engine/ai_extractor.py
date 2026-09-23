import httpx
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from engine.search_index import normalize_text

OLLAMA_URL = "http://localhost:11434"

class AIExtractor:
    """Intelligent value extractor using local Ollama models (Qwen 2.5 / Llava)."""
    
    def __init__(self, ollama_url: str = OLLAMA_URL):
        self.ollama_url = ollama_url

    async def list_available_models(self) -> List[str]:
        """Fetch list of models available in local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.ollama_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return ["qwen2.5:1.5b", "llama3.2:3b", "llava:7b"]

    def build_pruned_context(self, document_data: Dict[str, Any], target_fields: List[str], max_chars: int = 3500) -> Tuple[str, List[int]]:
        """
        Smart Context Pruning:
        Finds and compiles text from the most relevant pages matching target fields,
        keeping prompt size tight (< 600 tokens) for sub-second inference.
        """
        pages = document_data.get("pages", [])
        if not pages:
            return "", []

        # If document is short (<= 3 pages), include all
        if len(pages) <= 3:
            all_text = []
            pages_used = []
            for p in pages:
                content = p.get("text", "") or p.get("ocr_text", "")
                if content:
                    all_text.append(f"--- PÁGINA {p['page']} ---\n{content}")
                    pages_used.append(p["page"])
            return "\n\n".join(all_text)[:max_chars], pages_used

        # Score pages by presence of target field keywords
        scores = []
        clean_fields = [normalize_text(f) for f in target_fields if f.strip()]

        for p in pages:
            combined = (p.get("text", "") + "\n" + p.get("ocr_text", ""))
            # Also append image OCR
            for img in p.get("images", []):
                combined += "\n" + img.get("ocr_text", "")
            
            norm_combined = normalize_text(combined)
            score = 0
            for f in clean_fields:
                if f in norm_combined:
                    score += 5
                # Check individual words in field
                for word in f.split():
                    if len(word) > 3 and word in norm_combined:
                        score += 1

            scores.append((score, p["page"], combined))

        # Sort pages by relevance score
        scores.sort(key=lambda x: x[0], reverse=True)

        selected_snippets = []
        pages_used = []
        total_len = 0

        # Pick top pages (or first 2 pages if no specific matches)
        top_pages = scores[:4]
        # Always ensure page 1 (cover / header) is considered if relevant
        top_page_nums = {x[1] for x in top_pages}
        if 1 not in top_page_nums and len(pages) > 0:
            top_pages.append((0, 1, pages[0].get("text", "") or pages[0].get("ocr_text", "")))

        # Sort by actual page number
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

        return "\n".join(selected_snippets), pages_used

    async def extract_values(
        self,
        document_data: Dict[str, Any],
        target_fields: List[str],
        model: str = "qwen2.5:1.5b"
    ) -> Dict[str, Any]:
        """
        Extract requested values using LLM with pruned context and strict JSON formatting.
        """
        start_time = time.perf_counter()

        if not target_fields:
            return {
                "values": {},
                "model_used": model,
                "latency_seconds": 0.0,
                "pages_consulted": []
            }

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

        extracted_data = {}
        error_msg = None

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 300
                        }
                    }
                )
                
                if res.status_code == 200:
                    data = res.json()
                    raw_response = data.get("response", "{}")
                    try:
                        extracted_data = json.loads(raw_response)
                    except json.JSONDecodeError:
                        # Fallback extraction if model enclosed in markdown backticks
                        clean_json = raw_response.strip()
                        if clean_json.startswith("```"):
                            clean_json = clean_json.split("\n", 1)[1]
                            clean_json = clean_json.rsplit("```", 1)[0]
                        extracted_data = json.loads(clean_json)
                else:
                    error_msg = f"Ollama error {res.status_code}: {res.text}"
        except Exception as e:
            error_msg = f"Error al conectar con el modelo IA: {str(e)}"
            # Provide empty fields on error so UI doesn't crash
            extracted_data = {f: "Error al consultar modelo" for f in target_fields}

        elapsed = round(time.perf_counter() - start_time, 3)

        return {
            "values": extracted_data,
            "model_used": model,
            "latency_seconds": elapsed,
            "latency_ms": round(elapsed * 1000, 1),
            "pages_consulted": pages_used,
            "error": error_msg
        }
