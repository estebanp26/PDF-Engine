# Instalación y ejecución — PDF-Engine

> Documento complementario a [DOCUMENTACION_PROYECTO.md](DOCUMENTACION_PROYECTO.md).
> Los comandos corresponden a los del repositorio real (`run.sh`, `README.md` y comandos de las guías de desarrollo).

---

## 1. Requisitos previos

| Software | Versión mínima declarada | Verificado en auditoría |
| --- | --- | --- |
| Python | 3.12+ | 3.12.3 |
| uv | recomendado (alternativa: `python3 -m venv`) | disponible (`/home/dylan/.local/bin/uv`) |
| Node.js | 18+ | 22.23.3 |
| Tesseract OCR | 5.x | 5.3.4 (idiomas instalados: `eng`, `spa`, `osd`) |
| Ollama | — (servicio local) | corriendo en `localhost:11434` |
| Modelo de IA | `qwen2.5:1.5b` (recomendado) o `qwen2.5:0.5b` | ambos detectados |

---

## 2. Dependencias de sistema

```bash
# Tesseract (obligatorio para OCR de escaneos). Para distribuciones basadas en Debian:
sudo apt install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng

# Verificar idiomas instalados (deben aparecer spa y eng):
tesseract --list-langs
```

---

## 3. Modelo de IA local (Ollama)

```bash
# Levantar el servidor de Ollama (si no está como servicio):
ollama serve

# Descargar el modelo (en otra terminal):
ollama pull qwen2.5:1.5b      # recomendado; 0.5b para CPUs modestas
```

El servidor se comprueba en el arranque: `curl http://localhost:11434/api/tags` debe responder. Si no, la aplicación **funciona** para lectura, OCR, búsqueda y vista previa, pero la extracción IA y el Q&A devolverán errores de conexión (ver sección 10).

---

## 4. Instalación de dependencias Python

```bash
# Desde la raíz del repositorio

# Opción A: con uv (recomendada por run.sh)
uv venv .venv
uv pip install --python .venv/bin/python3 -r requirements.txt

# Opción B: con pip estándar
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> **Nota:** `requirements.txt` incluye `numpy>=1.24.0`, que es utilizado activamente por `engine/ocr_engine.py` para operaciones de filtrado vectorial y sustracción de fondo en la detección de marcas de agua y logos, y `augly>=1.0.0` que es una dependencia residual no importada en el runtime. La instalación de esta última puede demorarse unos minutos.

Dependencias de desarrollo:

```bash
uv pip install --python .venv/bin/python3 -r requirements-dev.txt   # añade pytest
```

---

## 5. Instalación del frontend

```bash
cd frontend
npm install
npm run build          # genera frontend/dist (lo sirve el backend)
cd ..
```

Scripts disponibles en `frontend/package.json`:

| Script | Comando | Uso |
| --- | --- | --- |
| dev | `npm run dev` | Servidor de desarrollo Vite (puerto 5173, proxy/API → 8001). |
| build | `npm run build` | Build de producción (vite build). |
| lint | `npm run lint` | Análisis estático con oxlint. |
| preview | `npm run preview` | Previsualización local del build. |

---

## 6. Ejecución

### Opción 1: Lanzador automático (`./run.sh`)

`run.sh` (bash) hace de forma automática:

1. Crea `.venv` si no existe (con `uv` o `python3 -m venv`).
2. Instala las dependencias Python si `fastapi`/`uvicorn` no importan.
3. Compila el frontend si `frontend/dist` no existe o `frontend/src` es más nuevo que `dist/index.html`.
4. Comprueba Ollama y muestra una advertencia si no está corriendo.
5. Arranca `uvicorn server:app --host 0.0.0.0 --port 8001 --reload`.

```bash
./run.sh
```

Abrir **http://localhost:8001**.

### Opción 2: Manual

```bash
.venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

> Con `--reload` el servidor se reinicia automáticamente al modificar archivos Python (útil para desarrollo).

### Desarrollo frontend aislado

Con el backend en 8001, en otra terminal:

```bash
cd frontend && npm run dev    # http://localhost:5173 (proxya /api a 8001)
```

---

## 7. Ejecución de las pruebas

```bash
.venv/bin/python3 -m pytest tests/ -q
```

**Resultado verificado:**

```text
34 passed in 3.58s
```

- 2 pruebas (`test_ocr_worker_reads_text`, `test_ocr_batch_parallel`) requieren Tesseract instalado y se omiten automáticamente si no está.
- Las pruebas de IA (`test_ai_extractor.py`) **no requieren Ollama**: simulan (`monkeypatch`) la respuesta del modelo.

Para detalle:

```bash
.venv/bin/python3 -m pytest tests/ -v
```

---

## 8. Benchmarks

```bash
# Benchmark integral: genera samples/benchmark_20_pages.pdf y mide
# lectura+OCR, búsqueda y extracción IA (requiere Tesseract; Ollama opcional)
.venv/bin/python3 test_benchmark.py

# Barrido de afinación OCR: workers [1,2,4,6,8,12] y DPI [100,150,175,200,250]
.venv/bin/python3 benchmarks/benchmark_ocr_tuning.py
.venv/bin/python3 benchmarks/benchmark_ocr_tuning.py --dpi-only
```

> La etapa de IA del benchmark tarda del orden de minutos en CPU sin GPU (ver limitaciones).

---

## 9. Variables de entorno / configuración

**No existen variables de entorno** en la versión actual. Los parámetros operativos están fijos en el código:

| Parámetro | Valor | Dónde cambiarlo |
| --- | --- | --- |
| Puerto del servidor | `8001` | `run.sh:64` (arg de uvicorn) |
| URL de Ollama | `http://localhost:11434` | `engine/ai_extractor.py:8` |
| Modelo por defecto | `qwen2.5:1.5b` | `engine/ai_extractor.py:9` |
| Tamaño máximo de subida | 50 MB | `server.py:44` |
| Máximo de páginas | 300 | `server.py:45` |
| DPI de OCR | 150 | `pdf_reader.py:64` |
| DPI de vista previa | 120 | `server.py:329` |
| Conteo de caché LRU | 3 | `pdf_reader.py:41` |

---

## 10. Problemas conocidos

| Problema | Causa | Mitigación |
| --- | --- | --- |
| La extracción IA tarda 1–4 min | Modelo local en CPU sin GPU (~1 token/s) | Usar `qwen2.5:0.5b`; máquina con mejor CPU/GPU para producción. El timeout del cliente es de 300 s. |
| OCR lento en PDFs grandes | Depende de DPI y número de workers | Ejecutar `benchmarks/benchmark_ocr_tuning.py` para ajustar worker/DPI en la máquina de despliegue. |
| La IA no responde / errores "Ollama" | Ollama no corriendo o modelo no descargado | `ollama serve` y `ollama pull qwen2.5:1.5b`; verificar `curl localhost:11434/api/tags`. |
| Tesseract no reconoce textos en español | Faltan los idiomas `spa` | `sudo apt install tesseract-ocr-spa`; verificar `tesseract --list-langs`. |
| Se espera doble OCR y no ocurre | Por diseño: deduplicación de OCR de página + imagen dominante | No es un error; es el comportamiento documentado. |
| Documento "desaparece" al reiniciar o al subir otro | Estado del documento en memoria (un solo documento activo) | Volver a subir; no está pensado para multi-usuario. |
| `numpy`/`augly` se instalan pero no se usan | Dependencias muertas en `requirements.txt` | Ignorar o eliminar tras validación del equipo. |
| El frontend muestra "OCR Paralelo (12 Hilos)" con otro pool | Texto fijo del KPI (`KpiStrip.jsx:55`), no refleja el pool real | Cosmético; el pool real se calcula por CPU. |

---

## 11. Comprobación rápida (smoke test)

```bash
curl http://localhost:8001/api/system-status

# 1) Cargar el documento de ejemplo
JOB=$(curl -s -X POST http://localhost:8001/api/load-sample \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# 2) Esperar procesamiento
until curl -s http://localhost:8001/api/progress/$JOB | grep -q '"status":"done"'; do sleep 1; done

# 3) Consultar documento y buscar
curl -s http://localhost:8001/api/document/$JOB | python3 -m json.tool | head -40
curl -s -X POST http://localhost:8001/api/search \
  -H 'Content-Type: application/json' -d '{"query":"FACTURA"}'
```

El flujo completo (cargar → progreso → documento → búsqueda) fue verificado de forma real en la auditoría (20 páginas, ~12.3 s de procesamiento en CPU de 2 núcleos).