# PDF-Engine

> Motor de procesamiento de documentos PDF con OCR paralelo (Tesseract), índice de
> búsqueda léxico instantáneo, normalización inteligente y extracción de valores con IA local (Qwen 2.5 vía Ollama).

Sin modelos de visión pesados (torch/transformers/LLaVA). Sin AugLy en el runtime. Motor optimizado con Pillow y NumPy para preprocesamiento ultrarrápido.

---

## Características

- **Lectura PyMuPDF (C-level)**: texto digital con coordenadas por palabra en milisegundos.
- **OCR inteligente "solo donde hace falta"**:
  - Las páginas con texto digital suficiente **no** se mandan a OCR.
  - Las páginas escaneadas se procesan con *deduplicación*: si el escaneo es una imagen
    predominante (≥50 % de la página) se OCR ese PNG a resolución nativa; si no, se
    renderiza la página completa al DPI configurado. Nunca se hace doble OCR del mismo contenido.
  - Pool paralelo de workers con preprocesado "Anti-Todo" adaptativo (contraste dinámico, preservación de tickets estrechos y supresión de sombras de escáner al 0.8%).
  - **Pase de alta frecuencia para logos y marcas de agua**: detección en encabezados mediante sustracción de fondo local gaussiana y `--psm 11`, recuperando tipografías tenues, punteadas (matriz de punto) y sellos que el segmentador de página descarta como ilustraciones.
- **Limpiador y normalizador léxico (`FastVocabCleaner`)**:
  - Diccionario especializado (términos médicos, farmacéuticos, institucionales, financieros y administrativos).
  - Corrección fonética/ortográfica de artefactos típicos de OCR y restitución de mayúsculas/minúsculas y tildes originales.
- **Índice de búsqueda multinivel con coordenadas**: `word ➜ {página, fuente, coordenadas x0/y0/x1/y1}`
  para texto digital, OCR de escaneos e imágenes; resaltado de cajas en el visor.
  - Jerarquía de búsqueda: **exacto ➔ prefijo (predictivo / palabras incompletas, ej. "doc" ➔ "doctor") ➔ subcadena interna ➔ difuso** (difflib ≥ 82 %).
  - **Tokens compuestos y códigos**: cadenas como `CO9CA0101-LOSARTÁN` o `CC-1043448102` indexan tanto el token completo como sus subcomponentes (`losartan`, `co9ca0101`).
  - **Normalización de documentos de identidad y códigos MRZ**: números con puntos (`1.043.589.150`, `32.848.952`) y secuencias numéricas de 6–12 dígitos en líneas MRZ se indexan limpios sin puntuación, asociando las coordenadas espaciales exactas.
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
      ├─ get_text("words") ───────────► índice de coordenadas (texto digital + sub-tokens + IDs)
      │
      ├─ ¿página con texto útil ≥ 30 chars?     ──► NO  →  página "escaneada"
      │        │  SÍ
      │        │     └─ ¿imagen dominante (≥50%)? ──► SÍ → OCR del PNG nativo
      │        │
      │        └─ OCR de imágenes embebidas (contenido suplementario)
      └─ si no hay imagen buena ──► render de página completa a DPI (dedup)
                      │
                      ▼
      OCR paralelo (pools de workers, Preprocesado Anti-Todo + Pase de Logo/Watermark)
                      │
                      ▼
      Limpieza de vocabulario (FastVocabCleaner) + Mapeo de cajas px ➜ puntos PDF
                      │
                      ▼
      Índice léxico combinado: texto + ocr + image_ocr (sub-tokens, números limpios, coords)
                      │
             ┌────────┴─────────┐
             ▼                  ▼
      Búsqueda exacto ➔ prefijo ➔ subcadena ➔ fuzzy     IA Qwen 2.5 (contexto podado, JSON)
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

> `requirements.txt` depende de pymupdf, pytesseract, pillow, numpy, fastapi, uvicorn,
> httpx, python-multipart y pydantic. `requirements-dev.txt` añade pytest.

---

## Tests

```bash
.venv/bin/python3 -m pytest tests/ -v
```

**34 pruebas automáticas (todas pasando en ~3.5 s):**
- `tests/test_pdf_reader.py`: lectura de PDFs digitales/escaneados/corruptos, deduplicación de OCR, caché SHA-256, sin render innecesario.
- `tests/test_ocr_engine.py`: preprocesado Anti-Todo, escalado adaptativo, pase de logos/watermarks de alta frecuencia, tolerancia a bytes corruptos, OCR real en español.
- `tests/test_search_index.py`: coincidencia exacta, normalización de acentos/case, búsqueda por prefijo (palabras incompletas), subcadenas, difuso Levenshtein, búsqueda de frases, sub-tokens y coordenadas en puntos PDF.
- `tests/test_vocab_cleaner.py`: limpieza léxica, restitución de display forms, correcciones ortográficas automáticas de OCR.
- `tests/test_ai_extractor.py`: extracción estructurada, tolerancia a JSON inválido, guardia de no-invención/alucinación, poda de contexto.

## Benchmark

```bash
.venv/bin/python3 test_benchmark.py
.venv/bin/python3 benchmarks/benchmark_ocr_tuning.py   # barrido workers 1-12 y DPI 100-250
```

Resultados medidos en la máquina de desarrollo actual (CPU 2 núcleos, OCR Tesseract 5.3.4, IA `qwen2.5:0.5b` en CPU sin GPU):

| Etapa | Escenario | Resultado |
| :--- | :--- | :--- |
| **PDF Mixto Corporativo (20 páginas)** | 12 digitales + 4 con imagen + 4 escaneos | ~12.3 s (8 ítems OCR deduplicados) |
| **PDF Documental / Salud / ID (8 páginas)** | Facturas térmicas, fórmulas médicas, cédulas col. anverso y reverso | **~3.4 s** (OCR paralelo + pase de watermark + indexación) |
| **Búsqueda léxica multinivel** | Exacto, prefijo, subcadena o fuzzy con coordenadas | **~3–4 ms** por consulta |
| **Extracción IA de 5 campos** | Qwen 2.5 local (CPU 2 núcleos) | ~270 s (5/5 campos correctos con evidencia) |

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