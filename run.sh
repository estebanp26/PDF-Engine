#!/usr/bin/env bash
# PDF-Engine Enterprise Launcher (FastAPI Backend + React Vite Frontend)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

VENV_PYTHON="$DIR/.venv/bin/python3"

# 1. Setup virtual environment if missing
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[*] Entorno virtual no encontrado. Configurando dependencias..."
    if command -v uv &> /dev/null; then
        echo "[*] Utilizando uv (acelerado)..."
        uv venv "$DIR/.venv"
        source "$DIR/.venv/bin/activate"
        uv pip install -r "$DIR/requirements.txt"
    else
        echo "[*] Utilizando python3 -m venv estándar..."
        python3 -m venv "$DIR/.venv"
        source "$DIR/.venv/bin/activate"
        pip install --upgrade pip
        pip install -r "$DIR/requirements.txt"
    fi
fi

# Install Python dependencies if missing (handles broken/empty .venv too)
if ! "$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "[*] Instalando dependencias Python..."
    if command -v uv &> /dev/null; then
        uv pip install --python "$VENV_PYTHON" -r "$DIR/requirements.txt"
    else
        "$VENV_PYTHON" -m pip install -r "$DIR/requirements.txt"
    fi
fi

# 2. Build React + Vite frontend if dist is not built
if [ ! -d "$DIR/frontend/dist" ]; then
    echo "[*] Compilando frontend React + Vite + Tailwind..."
    cd "$DIR/frontend"
    npm install
    npm run build
    cd "$DIR"
fi

# 3. Check Ollama status
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "[!] ADVERTENCIA: Ollama no parece estar corriendo en localhost:11434."
    echo "    Para habilitar la IA ejecuta en otra terminal: ollama serve"
    echo "    Y asegúrate de tener el modelo: ollama pull qwen2.5:1.5b"
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
echo "👉 Abre tu navegador en: http://localhost:8001"
echo "======================================================================"

exec "$VENV_PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
