import re
import unicodedata
import difflib
from typing import List, Dict, Any, Set, Tuple, Optional

# Minimum similarity for fuzzy (OCR-resilient) fallback
FUZZY_RATIO = 0.82
# Fuzzy only kicks in after exact lookup misses, and only for words this long
FUZZY_MIN_LEN = 4


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


def _iter_sources(document_data: Dict[str, Any]):
    """Yield (page_num, src, image_id, label, original_text) across all sources."""
    for page in document_data.get("pages", []):
        p = page["page"]
        if page.get("text"):
            yield p, "text", None, "Texto Digital", page["text"]
        if page.get("ocr_text"):
            yield p, "ocr", None, "Escaneo de Página (OCR)", page["ocr_text"]
        for img in page.get("images", []):
            if img.get("ocr_text"):
                yield p, "image_ocr", img["id"], f"Imagen {img['id']} (OCR)", img["ocr_text"]


class SearchEngine:
    """Lexical search over prebuilt word index (exact -> fuzzy), no vector DB.

    Lookups resolve against a normalized word->coordinate index built at
    processing time (engine.pdf_reader), returning page, snippet and x0/y0/x1/y1
    (page points) so the UI can render an on-page highlight box.
    """

    @staticmethod
    def _build_index(document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build the word/pages index on the fly for docs without one (coords = None)."""
        word_locations: Dict[str, List[Dict[str, Any]]] = {}
        for page, src, image_id, _, text in _iter_sources(document_data):
            for match in re.finditer(r"[A-Za-zÁ-ÿ0-9ÁÉÍÓÚÜÑáéíóúüñ-]{2,}", text):
                word = match.group()
                norm = normalize_text(word)
                if len(norm) < 2:
                    continue
                word_locations.setdefault(norm, []).append({
                    "page": page, "src": "text" if src == "text" else src,
                    "x0": None, "y0": None, "x1": None, "y1": None,
                    "word": word,
                })
        return {
            "word_locations": word_locations,
            "pages_norm": {
                page: {
                    "text": normalize_text(text) if src == "text" else "",
                    "ocr": normalize_text(text) if src == "ocr" else "",
                    "images": [],
                }
                for page, src, _, _, text in _iter_sources(document_data)
            },
        }

    # ------------------------------------------------------------------ search
    @staticmethod
    def search(document_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"query": query, "tokens": [], "total_matches": 0,
                    "matched_pages": [], "results": []}

        raw_query = query.strip()
        norm_query = normalize_text(raw_query)
        raw_tokens = [w for w in re.split(r'[\s,\-_:\.;/]+', raw_query) if len(w) >= 2]
        tokens_norm = [normalize_text(w) for w in raw_tokens]

        if not tokens_norm:
            return {"query": query, "tokens": [], "total_matches": 0,
                    "matched_pages": [], "results": []}

        index = document_data.get("search_index") or SearchEngine._build_index(document_data)
        word_locations = index.get("word_locations", {})
        pages_indexed = index.get("pages_indexed", False)

        results: List[Dict[str, Any]] = []
        matched_pages_set: Set[int] = set()

        def source_text(page_num: int, src: str, image_id: Optional[str]) -> str:
            for page in document_data.get("pages", []):
                if page["page"] != page_num:
                    continue
                if src == "text":
                    return page.get("text", "")
                if src == "ocr":
                    return page.get("ocr_text", "")
                for img in page.get("images", []):
                    if img["id"] == image_id:
                        return img.get("ocr_text", "")
            return ""

        def source_label(src: str, image_id: Optional[str]) -> str:
            if src == "text":
                return "Texto Digital"
            if src == "ocr":
                return "Escaneo de Página (OCR)"
            return f"Imagen {image_id} (OCR)"

        phrase_query = " ".join(tokens_norm) if len(tokens_norm) > 1 else None

        # 1) EXACT / NORMALIZED match on the word index (fast, includes coords)
        for term in tokens_norm:
            for loc in word_locations.get(term, []):
                page = loc["page"]
                src = loc["src"]
                image_id = loc.get("image_id")
                txt = source_text(page, src, image_id)
                matched_term, snippet_text = _locate_word(txt, loc["word"])
                results.append({
                    "page": page,
                    "source": "image_ocr" if src == "image_ocr" else src,
                    "source_label": source_label(src, image_id),
                    "token_searched": loc["word"] or term,
                    "match_type": "exacto",
                    "snippet": snippet_text,
                    "matched_term": matched_term,
                    "image_id": image_id,
                    "x0": loc.get("x0"), "y0": loc.get("y0"),
                    "x1": loc.get("x1"), "y1": loc.get("y1"),
                })
                matched_pages_set.add(page)

        # 2) FUZZY fallback: only for tokens with zero exact hits, len >= 4,
        #    only against the vocabulary (much smaller than full text).
        vocab = sorted(word_locations.keys())
        vocab_by_first: Dict[str, List[str]] = {}
        for w in vocab:
            vocab_by_first.setdefault(w[0], []).append(w)

        for term in tokens_norm:
            if term in word_locations:
                continue  # already matched exactly
            if len(term) < FUZZY_MIN_LEN:
                continue
            candidates = vocab_by_first.get(term[0], [])
            best: List[Tuple[float, str]] = []
            for cand in candidates:
                if cand == term:
                    continue
                ratio = difflib.SequenceMatcher(None, term, cand).ratio()
                if ratio >= FUZZY_RATIO:
                    best.append((ratio, cand))
            best.sort(key=lambda t: t[0], reverse=True)
            for ratio, cand in best[:5]:
                for loc in word_locations[cand][:10]:
                    page = loc["page"]
                    src = loc["src"]
                    image_id = loc.get("image_id")
                    txt = source_text(page, src, image_id)
                    matched_term, snippet_text = _locate_word(txt, loc["word"])
                    results.append({
                        "page": page,
                        "source": "image_ocr" if src == "image_ocr" else src,
                        "source_label": source_label(src, image_id),
                        "token_searched": raw_query,
                        "match_type": f"difuso ({int(ratio*100)}%)",
                        "snippet": snippet_text,
                        "matched_term": matched_term,
                        "image_id": image_id,
                        "x0": loc.get("x0"), "y0": loc.get("y0"),
                        "x1": loc.get("x1"), "y1": loc.get("y1"),
                    })
                    matched_pages_set.add(page)

        # 3) PHRASE: multi-token queries collapse to a per-page/source match
        #    if every token appears on that page/source.
        if phrase_query:
            for page, src, image_id, label, txt in _iter_sources(document_data):
                norm_txt = normalize_text(txt)
                if all(t in norm_txt for t in tokens_norm):
                    # coordinates: use first token location on this page/source
                    coords = None
                    anchor_word = None
                    for t in tokens_norm:
                        for loc in word_locations.get(t, []):
                            if loc["page"] == page and _same_src(loc, src, image_id):
                                coords = (loc.get("x0"), loc.get("y0"),
                                          loc.get("x1"), loc.get("y1"))
                                anchor_word = raw_tokens[tokens_norm.index(t)]
                                break
                        if anchor_word:
                            break
                    matched_term, snippet_text = _locate_word(txt, anchor_word or raw_tokens[0])
                    results.append({
                        "page": page,
                        "source": "image_ocr" if src == "image_ocr" else src,
                        "source_label": label,
                        "token_searched": raw_query,
                        "match_type": "frase",
                        "snippet": snippet_text,
                        "matched_term": matched_term,
                        "image_id": image_id,
                        "x0": coords[0] if coords else None,
                        "y0": coords[1] if coords else None,
                        "x1": coords[2] if coords else None,
                        "y1": coords[3] if coords else None,
                    })
                    matched_pages_set.add(page)

        # Deduplicate identical (page, source, term, coords)
        dedup_keys: Set[Tuple[Any, ...]] = set()
        deduped: List[Dict[str, Any]] = []
        for r in results:
            k = (r["page"], r["source"], r["token_searched"], r["x0"], r["y0"])
            if k in dedup_keys:
                continue
            dedup_keys.add(k)
            deduped.append(r)
        deduped.sort(key=lambda r: (r["page"], r["source"]))

        return {
            "query": query,
            "tokens": raw_tokens,
            "total_matches": len(deduped),
            "matched_pages": sorted(list(matched_pages_set)),
            "indexed": len(word_locations) > 0 and not pages_indexed,
            "results": deduped,
        }


def _same_src(loc_src: str, src: str, image_id: Optional[str]) -> bool:
    if loc_src == "text" and src == "text":
        return True
    if loc_src == "ocr" and src == "ocr":
        return True
    return loc_src == "image_ocr" and (image_id is not None and src == "image_ocr")


def _locate_word(full_text: str, word: str) -> Tuple[str, str]:
    """Find the original term in the raw text (accent/case tolerant) + snippet."""
    if not full_text or not word:
        return word or "", ""
    m = re.search(re.escape(word), full_text, flags=re.IGNORECASE)
    if m:
        return full_text[m.start():m.end()], extract_snippet(full_text, m.start(), m.end())
    # accent-insensitive fallback
    norm_full = normalize_text(full_text)
    norm_word = normalize_text(word)
    idx = norm_full.find(norm_word)
    if idx >= 0:
        return word, extract_snippet(full_text, idx, idx + len(word))
    return word, ""