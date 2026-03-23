# setup.ps1 - One-click setup for BarkTTS on Windows
# Run from the BarkTTS folder:  .\setup.ps1
# Requires Python 3.9+ installed and on PATH.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== BarkTTS Setup ===" -ForegroundColor Cyan

# --- Check Python version ---
$pyver = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Install Python 3.10-3.12 from https://python.org" -ForegroundColor Red
    exit 1
}

$verMatch = $pyver -match "Python (\d+)\.(\d+)"
$major = [int]$Matches[1]
$minor = [int]$Matches[2]

Write-Host "Found: $pyver"

if ($major -ne 3 -or $minor -lt 9) {
    Write-Host "ERROR: Python 3.9 or newer is required. Found $major.$minor." -ForegroundColor Red
    Write-Host "       Download from https://python.org" -ForegroundColor Red
    exit 1
} elseif ($minor -ge 13) {
    Write-Host "NOTE: Python $major.$minor detected. Tested on 3.10-3.12; newer versions likely work fine." -ForegroundColor Yellow
}

# --- Clone Bark source repo if missing ---
if (Test-Path "bark") {
    Write-Host "bark/ already exists - skipping clone." -ForegroundColor Yellow
} else {
    Write-Host "Cloning suno-ai/bark..." -ForegroundColor Cyan
    git clone https://github.com/suno-ai/bark bark
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: git clone failed. Make sure git is installed and you have internet access." -ForegroundColor Red
        exit 1
    }
}

# --- Patch bark for PyTorch 2.6+ compatibility ---
# PyTorch 2.6 changed torch.load default to weights_only=True, breaking Bark's model loading.
$genFile = "bark\bark\generation.py"
$oldLine = '    checkpoint = torch.load(ckpt_path, map_location=device)'
$newLine = '    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)'
$content = Get-Content $genFile -Raw
if ($content -match [regex]::Escape($oldLine)) {
    Write-Host "Patching bark/bark/generation.py for PyTorch 2.6+ (weights_only=False)..." -ForegroundColor Cyan
    $content = $content.Replace($oldLine, $newLine)
    Set-Content $genFile $content -NoNewline
} else {
    Write-Host "bark/bark/generation.py already patched - skipping." -ForegroundColor Yellow
}

# --- Create venv ---
if (Test-Path "venv") {
    Write-Host "venv already exists - skipping creation." -ForegroundColor Yellow
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

# --- Activate ---
Write-Host "Activating venv..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# --- Install deps ---
Write-Host ""
Write-Host "Installing PyTorch with CUDA 12.4 support..." -ForegroundColor Cyan
Write-Host "NOTE: Installing torch from the PyTorch CUDA index (not PyPI)." -ForegroundColor Yellow
Write-Host "      Edit this line if you need CUDA 12.1 (cu121) or 11.8 (cu118)." -ForegroundColor Yellow
Write-Host ""

# Install torch FIRST using --index-url so CUDA build wins over PyPI CPU build
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyTorch install failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installing remaining dependencies..." -ForegroundColor Cyan

pip install -r requirements.txt

# --- Done ---
Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Activate the venv:" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test it (downloads ~5 GB of models on first run):" -ForegroundColor White
Write-Host "  python bark_tts.py 'Hello world' --play" -ForegroundColor Cyan
Write-Host ""

