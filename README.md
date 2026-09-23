# PDF-Engine Enterprise 🚀
> Motor de procesamiento ultrarrápido de documentos PDF (20+ páginas), OCR paralelo con Tesseract, resistencia Anti-Todo e Inteligencia Artificial (Qwen 2.5 / Llava).

Diseñado específicamente para competencias de velocidad y procesamiento masivo con precisión empresarial.

---

## ⚡ Rendimiento y Benchmarks (AMD Ryzen 5 5500U - 12 Hilos)

| Etapa | Tiempo (20 Páginas con 8 Escaneos/Fotos) | Tiempo (20 Páginas Texto Digital) |
| :--- | :--- | :--- |
| **Lectura y Parseo C-Level (PyMuPDF)** | ~0.41 s | **~0.05 s** |
| **OCR Paralelo Multiproceso (12 Hilos)** | ~4.04 s (8 escaneos ruidosos a 150 DPI) | 0.00 s (omitido si hay texto digital) |
| **Búsqueda Instantánea de Palabras Clave** | **5 a 9 ms** | **< 1 ms** |
| **Inferencia IA Estructurada (Qwen 2.5)** | **~1.2 s** (Contexto podado) | **~1.0 s** |
| **Tiempo Total Fin-a-Fin** | **~5.5 s** | **~1.2 s** |

---

## 🛠️ Arquitectura y Características

1. **Extracción Dual-Stream**:
   - Extrae streams de texto digital en milisegundos mediante bindings en C (`PyMuPDF`).
   - Extrae imágenes embebidas directamente de los objetos binarios (sin re-renderizar).
2. **Motor OCR "Anti-Todo"**:
   - Preprocesado en memoria: reescalado adaptativo (150–200 DPI), auto-contraste dinámico (elimina fondos amarillos y oscuros) y reducción de ruido.
   - Distribución paralela con `ProcessPoolExecutor` aprovechando el 100% de los hilos de la CPU.
3. **Barra de Búsqueda Omnipresente (Texto + Imágenes)**:
   - Búsqueda simultánea en texto digital, texto OCR de escaneos y texto OCR de imágenes.
   - Búsqueda insensible a mayúsculas, minúsculas, tildes y con coincidencia difusa (Fuzzy Matching) para tolerar errores leves de escáner.
4. **Extracción Inteligente de Valores con IA (Qwen 2.5)**:
   - Poda de contexto: en lugar de enviar 20 páginas a la IA, extrae solo las secciones relevantes (< 600 tokens).
   - Salida en JSON estructurado instantáneo.
5. **Frontend Empresarial Profesional**:
   - Diseño corporativo limpio, tipografía nítida, sin temas de juego ni efectos blur/glassmorphism.
   - Visor de páginas en alta resolución, cronómetro de precisión milimétrica y galería de imágenes.

---

## 🚀 Inicio Rápido

Para iniciar la aplicación con un solo comando:

```bash
./run.sh
```

Abre tu navegador en:
```
http://localhost:8000
```

Para ejecutar la prueba de benchmark por terminal:
```bash
./.venv/bin/python3 test_benchmark.py
```
