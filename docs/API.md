# Referencia de la API REST — PDF-Engine

> Documento complementario a [DOCUMENTACION_PROYECTO.md](DOCUMENTACION_PROYECTO.md).
> Todos los endpoints documentados existen en `server.py` y fueron verificados con ejecución real (excepto se indica lo contrario).

---

## 1. Generalidades

- **Base URL:** `http://localhost:8001` (predeterminada; ver `run.sh` y `INSTALACION.md`).
- **OpenAPI:** la aplicación FastAPI genera documentación interactiva en `/docs` (Swagger) y `/openapi.json` de forma automática.
- **Formato:** JSON salvo para rutas de imágenes/HTML.
- **Modelo de errores:** FastAPI devuelve `{"detail": "mensaje"}` con los códigos HTTP correspondientes.
- **CORS:** `allow_origins=["*"]`, `allow_credentials=True`, todos los métodos y cabeceras (server.py:23-29).

---

## 2. Tabla resumen de endpoints

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/` | Índice del frontend compilado (HTML). |
| GET | `/assets/*` | Estáticos del frontend (montado si existe `frontend/dist/assets`). |
| GET | `/api/system-status` | Estado del sistema. |
| POST | `/api/upload` | Sube un PDF y lanza el procesamiento. |
| POST | `/api/load-sample` | Genera y procesa el PDF de ejemplo de 20 páginas. |
| GET | `/api/progress/{job_id}` | Progreso de un job. |
| GET | `/api/document/{job_id}` | Documento procesado. |
| POST | `/api/search` | Búsqueda léxica. |
| POST | `/api/extract-ai` | Extracción de campos con IA. |
| POST | `/api/ask` | Pregunta-respuesta con evidencia. |
| GET | `/api/page-preview/{page_num}` | PNG de página con resaltado. |
| GET | `/api/extracted-image/{image_id}` | Bytes de una imagen extraída. |

---

## 3. Endpoints detallados

### 3.1 `GET /`

| Campo | Valor |
| --- | --- |
| Descripción | Sirve el `index.html` del build de React (`frontend/dist/index.html`). Si el frontend no está compilado, devuelve un HTML informativo. |
| Respuesta | `text/html` |

**Respuesta en ausencia de build:**

```html
<h1>PDF-Engine Enterprise</h1><p>Frontend no compilado. Ejecuta: cd frontend && npm run build</p>
```

### 3.2 `GET /assets/*`

| Campo | Valor |
| --- | --- |
| Descripción | Archivos estáticos generados por Vite (js, css, imágenes). Solo se monta si `frontend/dist/assets` existe (server.py:39-41). |
| Respuesta | Archivo estático del build. |

### 3.3 `GET /api/system-status`

| Campo | Valor |
| --- | --- |
| Descripción | Estado del sistema: núcleos de CPU, motor OCR, distribución de workers, modelos IA disponibles y modelo por defecto. |
| Respuesta | JSON |

**Respuesta real (auditoría):**

```json
{
  "status": "online",
  "cpu_cores": 2,
  "ocr_engine": "Tesseract 5.x (pool ~1 workers)",
  "ai_engine": "Qwen 2.5 via Ollama",
  "available_models": ["qwen2.5:1.5b", "qwen2.5:0.5b"],
  "default_model": "qwen2.5:1.5b"
}
```

> Nota: `ocr_engine` calcula el pool como `(os.cpu_count() or 4 + 1) // 2` (server.py:178); con 2 cores indica `~1 worker`, que coincide con la fórmula de `FastOCREngine` (`min(12, max(1, (cpus+1)//2))`).

### 3.4 `POST /api/upload`

| Campo | Valor |
| --- | --- |
| Descripción | Sube un archivo PDF, lo valida y lanza el procesamiento como job asíncrono. |
| Entrada (multipart) | `file`: archivo (obligatorio). `run_ocr`: booleano de formulario, default `true`. |
| Respuesta | `{job_id, status}` |

**Validaciones** (server.py:185-210):

- El archivo debe tener extensión `.pdf` (400 en caso contrario).
- Tamaño máximo 50 MB (400 si se excede; se borra el archivo parcial).
- PDF válido con ≤ 300 páginas (`_validate_pdf_file`).

**Respuesta:**

```json
{"job_id": "a1b2c3d4e5f6", "status": "running"}
```

### 3.5 `POST /api/load-sample`

| Campo | Valor |
| --- | --- |
| Descripción | Genera `samples/benchmark_20_pages.pdf` (si no existe) mediante `build_20_page_benchmark_pdf` y lo procesa. El PDF de ejemplo combina 12 páginas digitales, 4 con imágenes embebidas y 4 escaneos ruidosos. |
| Entrada | Sin cuerpo. |
| Respuesta | `{job_id, status}` |

### 3.6 `GET /api/progress/{job_id}`

| Campo | Valor |
| --- | --- |
| Descripción | Consulta el progreso de un job. |
| Entrada | `job_id` (path). |
| Respuestas | 404 si el job no existe. |

**Respuesta en curso (real):**

```json
{"job_id":"415f3d0c924e","status":"running","progress":{"stage":"ocr","percent":55,"ocr_done":5,"ocr_total":8}}
```

**Etapas posibles de `progress.stage`:** `parsing` (5→15 %), `ocr` (15→80 %), `indexing` (82 %), `finalizing` (95 %), `done` (100 %). Si el documento salió de caché, `progress` incluye `cache_hit: true`.

### 3.7 `GET /api/document/{job_id}`

| Campo | Valor |
| --- | --- |
| Descripción | Devuelve el documento procesado (payload ligero, sin bytes de imagen ni índice completo). |
| Entrada | `job_id` (path). |
| Respuestas | 404 si el job no existe; 500 con `detail` si el job falló; 202 "Procesamiento aún en curso" si no terminó. |

**Estructura de respuesta (resumen real):**

```json
{
  "success": true,
  "filename": "benchmark_20_pages.pdf",
  "total_pages": 20,
  "digital_pages": 16,
  "ocr_pages": 4,
  "ocr_items_processed": 8,
  "cached": false,
  "metrics": {
    "total_seconds": 12.3284,
    "total_ms": 12328.4,
    "pages_processed": 20,
    "pages_per_second": 1.62,
    "breakdown": { "pdf_open_and_parse": 0.6885, "parallel_ocr": 11.5942, "indexing": 0.0014 }
  },
  "pages": [
    {
      "page": 1,
      "text": "DOCUMENTO MAESTRO DE OPERACIONES Y SERVICIOS - RIWI TECH\n...",
      "is_scanned": false,
      "ocr_text": "",
      "has_images": false,
      "images": []
    }
  ]
}
```

**Página con imágenes (ejemplo de estructura):**

```json
{
  "page": 13,
  "text": "Página 13: Documento con Imagen Adjunta",
  "is_scanned": false,
  "ocr_text": "",
  "has_images": true,
  "images": [
    {
      "id": "p13_img1",
      "page": 13,
      "width": 800,
      "height": 450,
      "format": "png",
      "ocr_text": "RECIBO DE CAJA MENOR #4491 ..."
    }
  ]
}
```

> `_light_payload()` (server.py:86-113) omite `img["bytes"]` y el `search_index`.

### 3.8 `POST /api/search`

| Campo | Valor |
| --- | --- |
| Descripción | Búsqueda léxica sobre el documento activo. |
| Entrada | `{"query": "FACTURA"}` |
| Respuestas | 400 si no hay documento activo. |

**Respuesta real:**

```json
{
  "query": "FACTURA",
  "tokens": ["FACTURA"],
  "total_matches": 2,
  "matched_pages": [1, 17],
  "indexed": true,
  "results": [
    {
      "page": 1,
      "source": "text",
      "source_label": "Texto Digital",
      "token_searched": "Factura:",
      "match_type": "exacto",
      "snippet": "...Innovaciones Digitales del Norte S.A.S. NIT: 901.458.789-3 Número de Factura: FACT-2026-8849 ...",
      "matched_term": "Factura:",
      "image_id": null,
      "x0": 112.69, "y0": 139.54, "x1": 156.7, "y1": 156.03
    }
  ],
  "search_latency_ms": 3.02
}
```

**Campos de cada resultado:** `page`, `source` (`text`/`ocr`/`image_ocr`), `source_label`, `token_searched`, `match_type` (`exacto` / `prefijo` / `subcadena` / `difuso (NN%)` / `frase`), `snippet`, `matched_term`, `image_id`, `x0/y0/x1/y1` (coordenadas en puntos del PDF o `null`). `search_latency_ms` lo añade `server.py`.

- `exacto`: Coincidencia directa en el índice de palabras (incluyendo normalización de tildes, mayúsculas y correcciones léxicas de `FastVocabCleaner`).
- `prefijo`: Coincidencia por inicio de palabra / autocompletado para términos incompletos (ej. `"doc"` ➔ `"doctor"`, `"losart"` ➔ `"losartán"`).
- `subcadena`: Coincidencia interna dentro de palabras para términos de longitud ≥ 3 (ej. `"miento"` ➔ `"medicamento"`).
- `difuso (NN%)`: Fallback difuso mediante similitud difflib / Levenshtein (ratio ≥ 82%) para términos de longitud ≥ 4 sin coincidencias directas.
- `frase`: Coincidencia de frases de múltiples palabras consecutivas en la misma página/fuente.

### 3.9 `POST /api/extract-ai`

| Campo | Valor |
| --- | --- |
| Descripción | Extrae los campos solicitados del documento activo con Qwen 2.5. |
| Entrada | `{"fields": ["Número de Factura", "NIT"], "model": "qwen2.5:1.5b"}` (`model` opcional). |
| Respuestas | 400 si no hay documento activo. En backend el job es síncrono; la latencia depende del hardware (1–4 min en CPU). |

**Estructura de respuesta:**

```json
{
  "values": { "Número de Factura": "FACT-2026-8849", "NIT": "901.458.789-3" },
  "model_used": "qwen2.5:1.5b",
  "latency_seconds": 145.2,
  "latency_ms": 145200.0,
  "pages_consulted": [1],
  "error": null
}
```

Comportamiento en fallo: si el modelo no responde/JSON inválido, cada campo se rellena con `"No encontrado"` y `error` contiene el motivo (ai_extractor.py:186-189).

### 3.10 `POST /api/ask`

| Campo | Valor |
| --- | --- |
| Descripción | Responde una pregunta sobre el documento usando búsqueda léxica como evidencia + Qwen 2.5. |
| Entrada | `{"question": "¿Cuál es el valor total?", "model": "qwen2.5:1.5b"}` (`model` opcional). |
| Respuestas | 400 si no hay documento activo. |

**Respuesta (con evidencia):**

```json
{
  "question": "¿Cuál es el valor total de la factura?",
  "answer": "2.500.000",
  "unit": "COP",
  "page": 1,
  "evidence": "Monto: 2500000",
  "confidence": 0.94,
  "model_used": "qwen2.5:1.5b",
  "latency_seconds": 143.0,
  "latency_ms": 143000.0,
  "pages_consulted": [1],
  "error": null
}
```

**Respuesta (sin evidencia — no invoca al LLM):**

```json
{
  "question": "palabra_no_existe_999",
  "answer": null,
  "unit": null,
  "page": null,
  "evidence": null,
  "confidence": 0,
  "model_used": "qwen2.5:1.5b",
  "latency_ms": 0.0,
  "error": null,
  "reason": "Sin evidencia relevante para la pregunta."
}
```

**Pregunta vacía:**

```json
{"question": "", "answer": null, "unit": null, "page": null, "evidence": null,
 "confidence": 0, "model_used": "qwen2.5:1.5b", "latency_ms": 0.0,
 "error": "Pregunta vacía."}
```

### 3.11 `GET /api/page-preview/{page_num}`

| Campo | Valor |
| --- | --- |
| Descripción | Render de la página a 120 DPI (PNG) con resaltado opcional. |
| Parámetros | `page_num` (path), `highlight` (query, texto a resaltar en capa digital), `rects` (query, JSON de cajas `[[x0,y0,x1,y1], ...]`). |
| Respuestas | 404 sin documento cargado; 400 página fuera de rango; `image/png`. |

Comportamiento (server.py:282-338):

1. Si `rects` es JSON válido, añade anotaciones de resaltado con coordenadas explícitas.
2. Si `highlight` existe, tokeniza y usa `page.search_for(term)` sobre la capa de texto digital para añadir más resaltados.
3. Renderiza el pixmap a 120 DPI, devuelve PNG y borra las anotaciones temporales.

**Verificado en auditoría:** respuesta de 992×1404 px (PNG) para página A4 a 120 DPI.

### 3.12 `GET /api/extracted-image/{image_id}`

| Campo | Valor |
| --- | --- |
| Descripción | Devuelve los bytes originales de una imagen embebida extraída. |
| Entrada | `image_id` (path), p. ej. `p13_img1`. |
| Respuestas | 404 sin documento o imagen no encontrada; `image/jpeg` o `image/png` según formato. |

---

## 4. Códigos de error más frecuentes

| Código | Contexto |
| --- | --- |
| 202 | `GET /api/document/{job_id}` cuando el job aún procesa. |
| 400 | Extensión no `.pdf`, archivo > 50 MB, PDF corrupto/inválido, > 300 páginas, sin documento activo en search/extract/ask, página fuera de rango. |
| 404 | Job inexistente, documento no cargado para preview/imagen, imagen no encontrada. |
| 500 | Job en estado `error` (detalle en `detail`). |

---

## 5. Notas de uso en el cliente (frontend)

- **Subida:** `FormData` con `file` (multiplicidad `multipart/form-data`).
- **Progreso:** polling de `GET /api/progress/{job_id}` cada 400 ms (App.jsx:90-124).
- **Resaltado:** el visor construye `rects` a partir de las coordenadas del resultado de búsqueda y añade `t=Date.now()` como anti-caché (ViewerTab.jsx).
- **Modelos:** `/api/system-status` publica `available_models`; el frontend permite elegir el modelo para extracción y Q&A.