# =============================================================================
# XTTS API - Installation Script (Windows PowerShell)
# =============================================================================
# Run with: powershell -ExecutionPolicy Bypass -File install.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$PYTHON_VERSION = "3.10"
$MODEL_VERSION = "v2.0.3"
$TORCH_VERSION = "2.1.1"
$CUDA_VERSION = "cu118"

# =============================================================================
# Functions
# =============================================================================

function Write-Header {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Blue
    Write-Host "  XTTS API - Installation Script (PowerShell)" -ForegroundColor Blue
    Write-Host "===============================================" -ForegroundColor Blue
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Test-Command {
    param([string]$Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Download-File {
    param(
        [string]$Url,
        [string]$Output
    )

    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $Url -OutFile $Output -UseBasicParsing
        return $true
    }
    catch {
        return $false
    }
}

# =============================================================================
# Main Script
# =============================================================================

Write-Header

# -----------------------------------------------------------------------------
# Pre-requisites Check
# -----------------------------------------------------------------------------

Write-Step "Checking pre-requisites..."

# Check Python
if (-not (Test-Command "python")) {
    Write-Error "Python is not installed or not in PATH."
    Write-Host "Please install Python $PYTHON_VERSION from https://www.python.org/downloads/"
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Host "  - Python: $pythonVersion"

# Check pip
if (-not (Test-Command "pip")) {
    Write-Error "pip is not installed."
    exit 1
}
Write-Host "  - pip: installed"

# Check git
if (Test-Command "git") {
    Write-Host "  - git: installed"
} else {
    Write-Warning "git is not installed. Some features may not work."
}

# Check ffmpeg
if (Test-Command "ffmpeg") {
    Write-Host "  - ffmpeg: installed"
} else {
    Write-Warning "ffmpeg is not installed. Some audio features may not work."
    Write-Host "    Download from: https://ffmpeg.org/download.html"
}

Write-Host ""

# -----------------------------------------------------------------------------
# Virtual Environment
# -----------------------------------------------------------------------------

Write-Step "Setting up Python virtual environment..."

if (-not (Test-Path "venv")) {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
    Write-Success "Virtual environment created"
} else {
    Write-Warning "Virtual environment already exists"
}

# Activate virtual environment
$activateScript = ".\venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Success "Virtual environment activated"
} else {
    Write-Error "Failed to find activation script."
    exit 1
}

# Upgrade pip
python -m pip install --upgrade pip --quiet

Write-Host ""

# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------

Write-Step "Installing Python dependencies..."

pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies."
    exit 1
}

Write-Host ""
Write-Step "Installing PyTorch with CUDA $CUDA_VERSION..."

$torchInstall = pip install "torch==$TORCH_VERSION+$CUDA_VERSION" "torchaudio==$TORCH_VERSION+$CUDA_VERSION" --index-url "https://download.pytorch.org/whl/$CUDA_VERSION" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Failed to install PyTorch with CUDA. Trying CPU version..."
    pip install "torch==$TORCH_VERSION" "torchaudio==$TORCH_VERSION"
}

Write-Host ""

# -----------------------------------------------------------------------------
# Create Directories
# -----------------------------------------------------------------------------

Write-Step "Creating directories..."

$modelDir = "models\$MODEL_VERSION"
$speakersDir = "speakers"

if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
}

if (-not (Test-Path $speakersDir)) {
    New-Item -ItemType Directory -Path $speakersDir -Force | Out-Null
}

Write-Success "Directories created"

Write-Host ""

# -----------------------------------------------------------------------------
# Model Download
# -----------------------------------------------------------------------------

Write-Step "Checking XTTS model files..."

$configPath = "$modelDir\config.json"

if (-not (Test-Path $configPath)) {
    Write-Step "Downloading XTTS model files (this may take a while)..."

    $baseUrl = "https://huggingface.co/coqui/XTTS-v2/resolve/$MODEL_VERSION"

    Write-Host "  - Downloading config.json..."
    Download-File "$baseUrl/config.json" "$modelDir\config.json"

    Write-Host "  - Downloading vocab.json..."
    Download-File "$baseUrl/vocab.json" "$modelDir\vocab.json"

    Write-Host "  - Downloading model.pth (this is a large file ~1.8GB)..."
    Download-File "$baseUrl/model.pth" "$modelDir\model.pth"

    Write-Host "  - Downloading speakers_xtts.pth..."
    Download-File "$baseUrl/speakers_xtts.pth" "$modelDir\speakers_xtts.pth"

    Write-Success "XTTS model files downloaded successfully"
} else {
    Write-Warning "XTTS model files already exist, skipping download"
}

Write-Host ""

# -----------------------------------------------------------------------------
# Sample Speakers
# -----------------------------------------------------------------------------

Write-Step "Checking sample speaker files..."

$sampleUrl = "https://github.com/daswer123/xtts-api-server/raw/main/example"
$speakers = @("calm_female", "female", "male")

foreach ($speaker in $speakers) {
    $speakerPath = "$speakersDir\$speaker.wav"
    if (-not (Test-Path $speakerPath)) {
        Write-Host "  - Downloading $speaker.wav..."
        Download-File "$sampleUrl/$speaker.wav" $speakerPath
    }
}

Write-Success "Sample speakers ready"

Write-Host ""

# -----------------------------------------------------------------------------
# Additional Setup
# -----------------------------------------------------------------------------

Write-Step "Running additional setup..."

# Download spacy model for Portuguese
try {
    python -m spacy download pt_core_news_sm 2>$null
} catch {
    Write-Warning "Failed to download spacy model (optional)"
}

# Run model downloader script if exists
if (Test-Path "scripts\modeldownloader.py") {
    try {
        python scripts\modeldownloader.py 2>$null
    } catch {
        Write-Warning "Model downloader script failed (optional)"
    }
}

Write-Host ""

# -----------------------------------------------------------------------------
# Finish
# -----------------------------------------------------------------------------

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server:"
Write-Host ""
Write-Host "  1. Activate the virtual environment:"
Write-Host "     .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. Run the server:"
Write-Host "     python main.py"
Write-Host ""
Write-Host "  3. Access the API documentation:"
Write-Host "     http://localhost:8880/docs"
Write-Host ""

Read-Host "Press Enter to exit"
