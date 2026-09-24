#!/usr/bin/env bash
# PDF-Engine Enterprise Launcher (FastAPI Backend + React Vite Frontend)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

VENV_PYTHON="$DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[!] Entorno virtual no encontrado. Creando con uv..."
    uv venv "$DIR/.venv"
fi

# Install Python dependencies if missing (handles broken/empty .venv too)
if ! "$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "[*] Instalando dependencias Python..."
    uv pip install --python "$VENV_PYTHON" -r "$DIR/requirements.txt"
fi

# Build React + Vite frontend if dist is not built
if [ ! -d "$DIR/frontend/dist" ]; then
    echo "[*] Compilando frontend React + Vite + Tailwind..."
    cd "$DIR/frontend"
    npm install
    npm run build
    cd "$DIR"
fi

echo "======================================================================"
echo "🚀 PDF-ENGINE ENTERPRISE - REACT + VITE + TAILWIND + FASTAPI"
echo "======================================================================"
echo " • Núcleos CPU detectados: $(nproc) hilos lógicos"
echo " • OCR: Tesseract 5.x con aceleración paralela y filtros Anti-Todo"
echo " • Frontend: React + Vite + Tailwind CSS"
echo " • IA: Ollama (Qwen 2.5)"
echo " • Servidor iniciado en: http://localhost:8001"
echo "======================================================================"

exec "$VENV_PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
