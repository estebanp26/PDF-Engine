# PDF-Engine

> Motor de procesamiento de documentos PDF con OCR paralelo (Tesseract), índice de
> búsqueda léxico instantáneo y extracción de valores con IA local (Qwen 2.5 vía Ollama).

Sin LLaVA. Sin AugLy en el runtime. Sin dependencias pesadas de visión (torch/numpy).

---

## Características

- **Lectura PyMuPDF (C-level)**: texto digital con coordenadas por palabra en milisegundos.
- **OCR inteligente "solo donde hace falta"**:
  - Las páginas con texto digital suficiente **no** se mandan a OCR.
  - Las páginas escaneadas se OCR con *deduplicación*: si el escaneo es una imagen
    predominante (≥50 % de la página) se OCR ese PNG a resolución nativa; si no, se
    renderiza la página completa al DPI configurado. Nunca se hace doble OCR del mismo contenido.
  - Pool paralelo de workers con preprocesado "Anti-Todo" (re-escalado, contraste, ruido).
- **Índice de búsqueda preconstruido**: `word ➜ {página, fuente, coordenadas x0/y0/x1/y1}`
  para texto digital, OCR de escaneos e imágenes; resaltado de cajas en el visor.
  Orden de coincidencia: **exacto ➜ normalizado (tildes/case) ➜ difuso** (difflib ≥ 82 %).
- **Extracción IA con Qwen 2.5** (Ollama local, JSON estructurado):
  - `extract_values`: extraer campos concretos con contexto podado (solo páginas relevantes).
  - `ask`: respuesta a preguntas con evidencia citada, página y confianza; **no inventa**
    (confianza 0 y `answer: null` cuando no hay evidencia).
- **Procesamiento por jobs + progreso**: subida → `job_id` → polling de progreso por etapas
  → consulta del documento. UI con barra de progreso en vivo.
- **Caché por SHA-256** de los últimos N documentos procesados (LRU).

---

## Arquitectura

```
PDF guardado
      │
      ▼
  PyMuPDF (open/parse 1 paso)
      │
      ├─ get_text("words") ───────────► índice de coordenadas (texto digital)
      │
      ├─ ¿página con texto útil ≥ 30 chars?     ──► NO  →  página "escaneada"
      │        │  SÍ
      │        │     └─ ¿imagen dominante (≥50%)? ──► SÍ → OCR del PNG nativo
      │        │
      │        └─ OCR de imágenes embebidas (contenido suplementario)
      └─ si no hay imagen buena ──► render de página completa a DPI (dedup)
                      │
                      ▼
      OCR paralelo (pools de workers, Preprocesado Anti-Todo)
                      │
                      ▼
      Índice léxico combinado: texto + ocr + image_ocr (palabra ➜ coords)
                      │
             ┌────────┴─────────┐
             ▼                  ▼
      Búsqueda exacto→fuzzy   IA Qwen 2.5 (contexto podado, JSON)
```

### Pipeline del servidor

1. `POST /api/upload` o `/api/load-sample` → `{job_id}`.
2. `GET /api/progress/{job_id}` → etapa + porcentaje (polling del frontend).
3. `GET /api/document/{job_id}` → páginas, métricas, conteos digital/OCR.
4. `POST /api/search`, `POST /api/extract-ai`, `POST /api/ask` → operan sobre el documento activo.
5. `GET /api/page-preview/{page}` → PNG renderizado con cajas de resaltado (`rects`).

---

## Instalación

```bash
# Requisitos: Python 3.12+, uv, Node 18+, Tesseract 5.x (con spa y eng), Ollama

# Tesseract (obligatorio para OCR de escaneos)
sudo apt install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng

# Ollama + modelo (para extracción IA)
ollama pull qwen2.5:1.5b        # o 0.5b en máquinas CPU modestas

# Dependencias de Python (rápido: sin torch/agumently/numpy)
uv venv .venv
uv pip install --python .venv/bin/python3 -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..

# Levantar (puerto 8001) — o manual con uvicorn
./run.sh                          # opción automática
.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Abre `http://localhost:8001`.

> `requirements.txt` depende solo de pymupdf, pytesseract, pillow, fastapi, uvicorn,
> httpx, python-multipart y pydantic. `requirements-dev.txt` añade pytest.

---

## Tests

```bash
.venv/bin/python3 -m pytest tests/ -q
```

Cubre: lectura de PDFs digitales/escaneados/corruptos, deduplicación de OCR, caché,
búsqueda (exacto/tildes/fuzzy/frase/coordenadas), extracción IA y `ask` con Ollama
mockeado, y preprocesado OCR.

## Benchmark

```bash
.venv/bin/python3 test_benchmark.py
.venv/bin/python3 benchmarks/benchmark_ocr_tuning.py   # barrido workers 1-12 y DPI 100-250
```

Resultados medidos en la máquina de desarrollo actual (CPU 2 núcleos, sustituido OLlava
entorno, OCR Tesseract 5.3.4, IA `qwen2.5:0.5b` en CPU sin GPU):

| Etapa (PDF de 20 páginas: 12 digitales + 4 con imagen + 4 escaneos ruidosos) | Resultado |
| :--- | :--- |
| Lectura + parseo + índice (PyMuPDF) | ~12.3 s  (incluye OCR paralelo deduplicado, 8 ítems, sin doble OCR) |
| Búsqueda de palabra clave (exacto→fuzzy, con coordenadas) | **~3 ms** por consulta |
| Extracción IA de 5 campos (Qwen 2.5 local) | ~270 s en CPU de 2 núcleos (5/5 campos correctos) |

En hardware con GPU (o `qwen2.5:1.5b` en máquina dedicada) la latencia de IA baja de
varias órdenes de magnitud; OCR depende de DPI y número de workers (ver tuning script).

---

## Problemas y notas conocidas

- **Rendimiento IA en CPU**: el modelo Qwen local emite ~1 token/s en este equipo;
  cada llamada de extracción puede tardar 1–4 minutos. Es un límite de hardware, no del
  motor. Usa `qwen2.5:1.5b` en una máquina con mejor CPU/GPU para producción.
- **Modelo por defecto**: `DEFAULT_MODEL = "qwen2.5:1.5b"`. El servidor auto-detecta el
  primer modelo `qwen*` disponible en Ollama (`/api/system-status`), y el frontend permite
  elegirlo.
- **Frontend**: se entrega en React + Vite + Tailwind con sintaxis JSX (no TypeScript).
- **Nuevo flow por jobs**: el visor de página usa `rects` (cajas JSON) para resaltar hits;
  las coordenadas vienen del índice de búsqueda en puntos del PDF.