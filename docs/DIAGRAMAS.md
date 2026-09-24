# Diagramas — PDF-Engine

> Documento complementario a [DOCUMENTACION_PROYECTO.md](DOCUMENTACION_PROYECTO.md).
> Cada diagrama representa exclusivamente componentes y flujos que existen en el código real.

---

## 1. Diagrama de arquitectura del sistema

```mermaid
flowchart TD
    U[Usuario / Navegador] -->|HTTP| F[Frontend React SPA<br/>servido por FastAPI]
    F -->|fetch /api/...| API[FastAPI server.py<br/>puerto 8001]

    API --> UP[POST /api/upload<br/>POST /api/load-sample]
    API --> PR[GET /api/progress/{job_id}]
    API --> DOC[GET /api/document/{job_id}]
    API --> SR[POST /api/search]
    API --> AI[POST /api/extract-ai<br/>POST /api/ask]
    API --> PV[GET /api/page-preview]
    API --> EI[GET /api/extracted-image]

    UP --> READER[PDFEngineReader<br/>engine/pdf_reader.py]
    READER -->|hash SHA-256| CACHE[Cache LRU en memoria<br/>3 documentos]
    READER -->|imágenes/render| OCR[FastOCREngine<br/>engine/ocr_engine.py]
    OCR --> TESS[Tesseract 5.x<br/>spa+eng · pool de workers]
    READER --> IDX[Índice léxico word → coords]
    IDX --> SR2[SearchEngine<br/>engine/search_index.py]

    AI --> EX[AIExtractor<br/>engine/ai_extractor.py]
    EX -->|contexto podado + prompt JSON| OLL[Ollama local :11434]
    OLL --> QWEN[Qwen 2.5<br/>1.5b / 0.5b]
    QWEN --> EX
    EX --> AI

    API --> DISK[(uploads/ · samples/)]
    READER --> DISK
```

---

## 2. Flujo de procesamiento de un documento (pipeline)

Pipeline real de `PDFEngineReader.process_pdf` (engine/pdf_reader.py:60-317):

```mermaid
flowchart TB
    START[PDF recibido] --> H[sha256_file → hash]
    H --> CACHE{Caché LRU<br/>¿hash contenido?}
    CACHE -->|Sí| DONE1[Reutilizar resultado<br/>cached = true]
    CACHE -->|No| PARSE[Pass 1 · PyMuPDF parse + extraer]
    PARSE --> REV[Por cada página]
    REV --> TXT[get_text words → word_locations<br/>texto digital + coords]
    REV --> IMG[get_images → imágenes embebidas]
    TXT --> CLAS{texto útil < 30 chars?}
    CLAS -->|No · digital| NOOCR[Sin OCR de página]
    CLAS -->|Sí · escaneada| DOM{imagen dominante ≥ 50%?}
    DOM -->|Sí| OCRIMG[Cola OCR: PNG nativo<br/>scan único]
    DOM -->|No| REND[Render página completa<br/>DPI 150 → scan único]
    IMG -->|páginas digitales<br/>con imágenes| OCRIMGS[Cola OCR: imágenes embebidas]
    OCRIMG --> OCR[Pass 2 · OCR paralelo<br/>ProcessPoolExecutor]
    REND --> OCR
    OCRIMGS --> OCR
    OCR --> MAP[Pass 3 · mapear cajas<br/>px → puntos PDF]
    MAP --> MERGE[Merge texto OCR a páginas]
    MERGE --> IDX2[Construir search_index<br/>word_locations + pages_norm]
    IDX2 --> MET[SpeedProfiler → metrics]
    MET --> PUT[Caché: poner resultado]
    PUT --> DONE2[Documento listo]
    DONE1 --> DONE2
```

---

## 3. Flujo de búsqueda (prioridad de coincidencia)

Orden real de coincidencia de `SearchEngine.search` (engine/search_index.py:83-244):

```mermaid
flowchart TB
    Q[Consulta del usuario] --> TOK[Tokenizar + normalizar]
    TOK --> EXACT{¿término en<br/>word_locations?}
    EXACT -->|Sí| R1[Resultados exactos<br/>match_type = exacto]
    EXACT -->|No| FZ{len ≥ 4?}
    FZ -->|No| SKIP[Sin diferidos]
    FZ -->|Sí| SEQ[Comparar con difflib<br/>por primera letra]
    SEQ --> TH{ratio ≥ 0.82}
    TH -->|Sí| R2[Resultados difusos<br/>top 5 candidatos × 10 ubicaciones]
    TH -->|No| SKIP2[Sin coincidencia difusa]
    TOK --> PHRASE{¿más de 1 token?}
    PHRASE -->|Sí| ALL{¿todos los tokens<br/>en página/fuente?}
    ALL -->|Sí| R3[Resultado por frase<br/>match_type = frase]
    ALL -->|No| SKIP3[Sin coincidencia de frase]
    R1 --> DEDUP[Deduplicar (página, fuente, término, coords)]
    R2 --> DEDUP
    R3 --> DEDUP
    DEDUP --> OUT[Results + matched_pages + search_latency_ms]
```

---

## 4. Flujo de extracción de valores con IA

Flujo real de `AIExtractor.extract_values` (engine/ai_extractor.py:152-198):

```mermaid
flowchart TB
    F[fields solicitados] --> EMPTY{¿campos vacíos?}
    EMPTY -->|Sí| R0[Respuesta vacía<br/>sin llamar al modelo]
    EMPTY -->|No| PRUNE[build_pruned_context<br/>poda de contexto ≤ 3500 chars]
    PRUNE --> N{≤ 3 páginas?}
    N -->|Sí| ALLT[Todo el texto<br/>encabezado --- PÁGINA N ---]
    N -->|No| SCORE[Puntuar páginas por aparición<br/>de campos +5 / palabras +1]
    SCORE --> TOP[Top 4 + página 1 garantizada]
    TOP --> ALLT
    ALLT --> PROMPT[Construir prompt JSON en español]
    PROMPT --> GEN[POST /api/generate<br/>format json · temp 0.1 · num_predict 400]
    GEN --> PARSE{¿JSON válido?}
    PARSE -->|Sí| OK[values extraídos]
    PARSE -->|No| CLEAN[Limpiar ```/extraer primer {...}]
    CLEAN --> PARSE2{¿JSON válido?}
    PARSE2 -->|Sí| OK
    PARSE2 -->|No| NF[Campos = No encontrado<br/>+ error reportado]
    OK --> OUT[values + pages_consulted + latency + model_used]
    NF --> OUT
```

---

## 5. Flujo de pregunta-respuesta (Q&A)

Flujo real de `AIExtractor.ask` (engine/ai_extractor.py:201-289):

```mermaid
flowchart TB
    Q[Pregunta] --> NUL{¿pregunta vacía?}
    NUL -->|Sí| ERR[error = Pregunta vacía]
    NUL -->|No| SEARCH[SearchEngine.search<br/>sobre el documento]
    SEARCH --> EVID{Hay evidencia?}
    EVID -->|No| NOE[answer null · confidence 0<br/>sin invocar al LLM<br/>reason = Sin evidencia]
    EVID -->|Sí| HITS[Seleccionar hasta 5 fragmentos<br/>deduplicados página+fuente]
    HITS --> PROMPT[Prompt con evidencia<br/>+ reglas JSON estrictas]
    PROMPT --> GEN[Ollama /api/generate]
    GEN --> JSONR[Parsear JSON]
    JSONR --> SAN{answer == null?}
    SAN -->|Sí| NULLO[confidence = 0<br/>evidence = null]
    SAN -->|No| OK2[answer + unit + page + evidence + confidence]
    NULLO --> OUT2[Respuesta estructurada + latency]
    OK2 --> OUT2
    ERR --> OUT2
    NOE --> OUT2
```

---

## 6. Secuencia: carga de documento con progreso

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as SPA React
    participant API as FastAPI
    participant READER as PDFEngineReader
    participant OCR as OCR pool
    participant OLL as Ollama

    U->>F: Sube PDF / Benchmark
    F->>API: POST /api/upload | load-sample
    API->>API: validar .pdf, 50 MB, 300 pág
    API-->>F: {job_id}
    loop Cada 400 ms
        F->>API: GET /api/progress/{job_id}
        API-->>F: {stage, percent}
    end
    API->>READER: process_pdf (asyncio.to_thread)
    READER->>READER: sha256 + caché
    READER->>OCR: lote de imágenes/renders
    OCR-->>READER: texto + boxes
    READER-->>API: doc_data + index + metrics
    API->>API: activa documento (fitz)
    F->>API: GET /api/document/{job_id}
    API-->>F: payload ligero
    F-->>U: KPIs y UI lista
```

---

## 7. Secuencia: búsqueda y resaltado en visor

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as SPA React
    participant API as FastAPI
    participant SE as SearchEngine

    U->>F: Escribe consulta + Enter
    F->>API: POST /api/search {query}
    API->>SE: search(active_document, query)
    SE-->>API: results + coords
    API-->>F: {results, matched_pages, latency_ms}
    F->>F: pestaña resultados + salto a página
    U->>F: "Ver en Visor"
    F->>API: GET /api/page-preview/{p}?rects=[x0,y0,x1,y1]
    API->>API: render 120 DPI + add_highlight_annot
    API-->>F: PNG con cajas amarillas
```

---

## 8. Secuencia: extracción IA (poda de contexto)

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as SPA React
    participant API as FastAPI
    participant AI as AIExtractor
    participant OLL as Ollama Qwen

    U->>F: define campos / pregunta
    F->>API: POST /api/extract-ai | /api/ask
    alt Pregunta (ask)
        API->>AI: ask(doc, question)
        AI->>AI: búsqueda léxica → evidencia
    else Campos (extract_values)
        API->>AI: extract_values(doc, fields)
        AI->>AI: poda de contexto por puntuación
    end
    AI->>OLL: POST /api/generate (prompt, format=json)
    OLL-->>AI: respuesta cruda
    AI->>AI: parseo JSON + guardia anti-alucinación
    AI-->>API: JSON estructurado
    API-->>F: resultado
    F-->>U: tabla/ respuesta con confianza
```

---

## 9. Diagrama de componentes

```mermaid
flowchart LR
    subgraph Cliente
        B[Navegador · SPA React]
    end
    subgraph Backend[FastAPI · server.py]
        R1[API REST /api/*]
        R2[Estáticos /assets y /]
        R3[Jobs + progreso en memoria]
        R4[documento activo en memoria]
    end
    subgraph Motor[engine/]
        M1[PDFEngineReader]
        M2[FastOCREngine]
        M3[SearchEngine]
        M4[AIExtractor]
        M5[SpeedProfiler]
    end
    B --> R1
    B --> R2
    R1 --> R3
    R3 --> M1
    M1 --> R4
    R1 --> M3
    R1 --> M4
    M1 --> M2
    M1 --> M5
    M2 --> T[Tesseract 5.x]
    M4 --> O[Ollama · Qwen 2.5]
    M1 --> FS[(uploads/ · samples/)]
```

---

## 10. Grafo de actores y casos de uso

Modelo de casos de uso representado como grafo (más fiel al código real que un diagrama UML clásico por clases, al carecer el proyecto de casos detallados normalizados):

```mermaid
flowchart LR
    U[Usuario final] --> C1[CU1 · Cargar documento]
    U --> C2[CU2 · Buscar palabras]
    U --> C3[CU3 · Ver página con resaltado]
    U --> C4[CU4 · Extraer valores con IA]
    U --> C5[CU5 · Preguntar al documento]
    U --> C6[CU6 · Explorar imágenes extraídas]
    D[Desarrollador] --> C7[CU7 · Evaluar rendimiento]

    C1 --> S1[Motor PDF]
    C2 --> S1
    C3 --> S1
    C4 --> S2[Ollama · Qwen 2.5]
    C5 --> S2
    C4 --> S1
    C5 --> S1
    S1 --> S3[Tesseract 5.x]
```

> CU1–CU7 se describen en la sección 14 de [DOCUMENTACION_PROYECTO.md](DOCUMENTACION_PROYECTO.md) con precondiciones, flujos y alternativas. No existe caso de uso de autenticación porque no hay autenticación.

---

## 11. Ausencias intencionales de diagramas

| Diagrama | Motivo de ausencia |
| --- | --- |
| ERD / modelo de datos | El proyecto **no tiene base de datos** (no existen tablas ni colecciones). |
| Diagrama de C4 de despliegue | No hay despliegue multi-entorno (sin Docker, sin n8n, sin cloud) en el repositorio. |
| Diagrama de redes/RAG | No existe RAG vectorial ni embeddings; la recuperación es léxica. |