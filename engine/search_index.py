import unicodedata
import re
import difflib
from typing import List, Dict, Any, Set, Tuple

def normalize_text(text: str) -> str:
    """Normalize text: removes accents, diacritics, and converts to lowercase."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    stripped = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return stripped.lower()

def extract_snippet(full_text: str, match_start: int, match_end: int, window: int = 70) -> str:
    """Extract clean surrounding context snippet around the match."""
    start = max(0, match_start - window)
    end = min(len(full_text), match_end + window)
    
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(full_text) else ""
    
    raw_snippet = full_text[start:end].replace("\n", " ")
    snippet = " ".join(raw_snippet.split())
    return f"{prefix}{snippet}{suffix}"

class SearchEngine:
    """High-speed in-memory multi-token search across digital text and OCR images with Anti-Todo fuzzy resilience."""

    @staticmethod
    def search(document_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return {
                "query": query,
                "tokens": [],
                "total_matches": 0,
                "matched_pages": [],
                "results": []
            }

        raw_query = query.strip()
        norm_query = normalize_text(raw_query)

        # Extract individual search tokens (e.g. 'hablar ahora' -> ['hablar', 'ahora'])
        raw_tokens = [w for w in re.split(r'[\s,\-_:\.;/]+', raw_query) if len(w) >= 2]
        tokens_norm = [normalize_text(w) for w in raw_tokens]

        # Target terms to search: the full phrase (if >1 word) plus each individual word
        search_terms = []
        if len(tokens_norm) > 1 and len(norm_query) >= 3:
            search_terms.append((norm_query, "frase", raw_query))
        for t_orig, t_norm in zip(raw_tokens, tokens_norm):
            if (t_norm, "termino", t_orig) not in search_terms:
                search_terms.append((t_norm, "termino", t_orig))

        results: List[Dict[str, Any]] = []
        matched_pages_set: Set[int] = set()

        def scan_text_source(page_num: int, source_type: str, source_label: str, text: str, image_id: str = None):
            if not text:
                return
            
            norm_text = normalize_text(text)
            flex_text = re.sub(r'[\-_:\.]+', ' ', norm_text)
            
            seen_spans: Set[Tuple[int, int]] = set()

            for term_norm, term_kind, term_display in search_terms:
                flex_term = re.sub(r'[\-_:\.]+', ' ', term_norm).strip()
                term_matched = False

                # 1. Exact match
                for match in re.finditer(re.escape(term_norm), norm_text):
                    span = match.span()
                    if span not in seen_spans:
                        seen_spans.add(span)
                        term_matched = True
                        snippet = extract_snippet(text, span[0], span[1])
                        results.append({
                            "page": page_num,
                            "source": source_type,
                            "source_label": source_label,
                            "token_searched": term_display,
                            "match_type": "exacto" if term_kind == "termino" else "frase exacta",
                            "snippet": snippet,
                            "matched_term": text[span[0]:span[1]] if span[0] < len(text) else term_display,
                            "image_id": image_id
                        })
                        matched_pages_set.add(page_num)

                # 2. Flexible match (handling hyphens/spaces)
                if not term_matched and flex_term and flex_term != term_norm:
                    for match in re.finditer(re.escape(flex_term), flex_text):
                        span = match.span()
                        if span not in seen_spans:
                            seen_spans.add(span)
                            term_matched = True
                            snippet = extract_snippet(text, span[0], span[1])
                            results.append({
                                "page": page_num,
                                "source": source_type,
                                "source_label": source_label,
                                "token_searched": term_display,
                                "match_type": "flexible",
                                "snippet": snippet,
                                "matched_term": text[span[0]:span[1]] if span[0] < len(text) else term_display,
                                "image_id": image_id
                            })
                            matched_pages_set.add(page_num)

                # 3. Fuzzy match for resilient Anti-Todo OCR (for terms >= 4 chars)
                if not term_matched and len(term_norm) >= 4:
                    for word_match in re.finditer(r'\b\w{3,}\b', norm_text):
                        candidate = word_match.group()
                        ratio = difflib.SequenceMatcher(None, term_norm, candidate).ratio()
                        if ratio >= 0.82:
                            span = word_match.span()
                            if span not in seen_spans:
                                seen_spans.add(span)
                                snippet = extract_snippet(text, span[0], span[1])
                                results.append({
                                    "page": page_num,
                                    "source": source_type,
                                    "source_label": source_label,
                                    "token_searched": term_display,
                                    "match_type": f"difuso ({int(ratio*100)}%)",
                                    "snippet": snippet,
                                    "matched_term": text[span[0]:span[1]] if span[0] < len(text) else term_display,
                                    "image_id": image_id
                                })
                                matched_pages_set.add(page_num)

        # Iterate all pages
        for page in document_data.get("pages", []):
            page_num = page["page"]
            
            # Digital text
            scan_text_source(page_num, "text", "Texto Digital", page.get("text", ""))

            # Scanned page OCR
            scan_text_source(page_num, "page_scan_ocr", "Escaneo de Página (OCR)", page.get("ocr_text", ""))

            # Embedded images OCR
            for img in page.get("images", []):
                scan_text_source(page_num, "image_ocr", f"Imagen {img['id']} (OCR)", img.get("ocr_text", ""), image_id=img["id"])

        return {
            "query": query,
            "tokens": raw_tokens,
            "total_matches": len(results),
            "matched_pages": sorted(list(matched_pages_set)),
            "results": results
        }
