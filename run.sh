#!/usr/bin/env bash
# PDF-Engine Enterprise Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

VENV_PYTHON="$DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[!] Entorno virtual no encontrado. Creando con uv..."
    uv venv "$DIR/.venv"
    source "$DIR/.venv/bin/activate"
    uv pip install -r requirements.txt
fi

echo "======================================================================"
echo "🚀 PDF-ENGINE ENTERPRISE - MOTOR ACELERADO DE PROCESAMIENTO DOCUMENTAL"
echo "======================================================================"
echo " • Núcleos CPU detectados: $(nproc) hilos lógicos"
echo " • OCR: Tesseract 5.x con aceleración paralela y filtros Anti-Todo"
echo " • IA: Ollama (Qwen 2.5 / Llava)"
echo " • Servidor iniciado en: http://localhost:8000"
echo "======================================================================"

exec "$VENV_PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
