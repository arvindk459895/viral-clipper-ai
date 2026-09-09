#!/usr/bin/env bash
# ========================================================
# ViralClipper AI Studio - 1-Click Launcher (macOS / Linux)
# ========================================================

set -e

echo "========================================================"
echo "        ViralClipper AI Studio - Automated Launcher"
echo "========================================================"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    echo "Please install Python 3.10+ from https://www.python.org/downloads/ or via package manager."
    exit 1
fi

echo "[OK] Python detected: $(python3 --version)"

# 2. Check / Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    python3 -m venv .venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment found (.venv)."
fi

# 3. Activate Virtual Environment
source .venv/bin/activate

# 4. Install Dependencies
echo "[*] Checking and installing requirements..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "[OK] Python dependencies verified."

# 5. Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "[NOTICE] FFmpeg was not detected."
    echo "To install FFmpeg:"
    echo "  macOS:  brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y ffmpeg"
    echo ""
else
    echo "[OK] FFmpeg detected."
fi

# 6. Ensure required directories exist
mkdir -p outputs temp credentials

# 7. Launch Streamlit App
echo "========================================================"
echo " Launching ViralClipper AI Studio on http://localhost:8501"
echo "========================================================"
echo ""
streamlit run app.py
