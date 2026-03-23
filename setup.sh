#!/usr/bin/env bash
# setup.sh — One-click setup for BarkTTS on Linux / macOS
# Run from the BarkTTS folder:  bash setup.sh
# Requires Python 3.10–3.12 already installed.

set -e

echo ""
echo "=== BarkTTS Setup ==="

# ── Clone Bark source repo if missing ────────────────────────────────────────
if [ -d "bark" ]; then
    echo "bark/ already exists — skipping clone."
else
    echo "Cloning suno-ai/bark..."
    git clone https://github.com/suno-ai/bark bark
fi

# ── Find Python ───────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 9 ]; then
            PYTHON="$cmd"
            if [ "$MINOR" -ge 13 ]; then
                echo "Using Python $VER ($cmd) — tested on 3.10-3.12; newer versions likely work fine."
            else
                echo "Using Python $VER ($cmd)"
            fi
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.9 or newer not found."
    echo "Install from https://python.org or via your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
    echo "  macOS:         brew install python@3.12"
    exit 1
fi

# ── Create venv ───────────────────────────────────────────────────────────────
if [ -d "venv" ]; then
    echo "venv already exists — skipping creation."
else
    echo "Creating virtual environment..."
    "$PYTHON" -m venv venv
fi

# ── Activate ──────────────────────────────────────────────────────────────────
source venv/bin/activate

# ── Install deps ──────────────────────────────────────────────────────────────
echo ""
echo "Installing dependencies (this may take a few minutes)..."
echo "NOTE: PyTorch CUDA 12.4 will be installed by default."
echo "      Edit requirements.txt first if you need CUDA 12.1, 11.8, or CPU-only."
echo ""

pip install -r requirements.txt

# ── PortAudio for sounddevice (Linux) ─────────────────────────────────────────
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Linux detected — checking for PortAudio (needed for --play)..."
    if ! python -c "import sounddevice" &>/dev/null; then
        echo "  Install PortAudio: sudo apt install libportaudio2"
    else
        echo "  sounddevice OK."
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setup complete! ==="
echo ""
echo "Activate the venv:"
echo "  source venv/bin/activate"
echo ""
echo "Test it (downloads ~5 GB of models on first run):"
echo "  python bark_tts.py \"Hello world\" --play"
echo ""
