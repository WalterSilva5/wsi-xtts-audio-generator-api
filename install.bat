@echo off
setlocal enabledelayedexpansion

:: =============================================================================
:: XTTS API - Installation Script (Windows)
:: =============================================================================

title XTTS API - Installation

:: Configuration
set PYTHON_VERSION=3.10
set MODEL_VERSION=v2.0.3
set TORCH_VERSION=2.1.1
set CUDA_VERSION=cu118

:: Colors (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "NC=[0m"

:: =============================================================================
:: Header
:: =============================================================================

echo.
echo %BLUE%===============================================%NC%
echo %BLUE%  XTTS API - Installation Script (Windows)%NC%
echo %BLUE%===============================================%NC%
echo.

:: =============================================================================
:: Pre-requisites Check
:: =============================================================================

echo %GREEN%[STEP]%NC% Checking pre-requisites...

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Python is not installed or not in PATH.
    echo Please install Python %PYTHON_VERSION% from https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo   - Python: %PYTHON_VER%

:: Check pip
where pip >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% pip is not installed.
    pause
    exit /b 1
)
echo   - pip: installed

:: Check git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% git is not installed. Some features may not work.
) else (
    echo   - git: installed
)

:: Check ffmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% ffmpeg is not installed. Some audio features may not work.
    echo   Download from: https://ffmpeg.org/download.html
) else (
    echo   - ffmpeg: installed
)

echo.

:: =============================================================================
:: Virtual Environment
:: =============================================================================

echo %GREEN%[STEP]%NC% Setting up Python virtual environment...

if not exist "venv" (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo %RED%[ERROR]%NC% Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo %GREEN%[SUCCESS]%NC% Virtual environment created
) else (
    echo %YELLOW%[WARNING]%NC% Virtual environment already exists
)

:: Activate virtual environment
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Failed to activate virtual environment.
    pause
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% Virtual environment activated

:: Upgrade pip
python -m pip install --upgrade pip

echo.

:: =============================================================================
:: Dependencies
:: =============================================================================

echo %GREEN%[STEP]%NC% Installing Python dependencies...

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo %GREEN%[STEP]%NC% Installing PyTorch with CUDA %CUDA_VERSION%...

pip install torch==%TORCH_VERSION%+%CUDA_VERSION% torchaudio==%TORCH_VERSION%+%CUDA_VERSION% --index-url https://download.pytorch.org/whl/%CUDA_VERSION%
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% Failed to install PyTorch with CUDA. Trying CPU version...
    pip install torch==%TORCH_VERSION% torchaudio==%TORCH_VERSION%
)

echo.

:: =============================================================================
:: Create Directories
:: =============================================================================

echo %GREEN%[STEP]%NC% Creating directories...

if not exist "models\%MODEL_VERSION%" mkdir "models\%MODEL_VERSION%"
if not exist "speakers" mkdir "speakers"

echo %GREEN%[SUCCESS]%NC% Directories created

echo.

:: =============================================================================
:: Model Download
:: =============================================================================

echo %GREEN%[STEP]%NC% Checking XTTS model files...

set MODEL_DIR=models\%MODEL_VERSION%

if not exist "%MODEL_DIR%\config.json" (
    echo %GREEN%[STEP]%NC% Downloading XTTS model files (this may take a while)...

    echo   - Downloading config.json...
    powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/coqui/XTTS-v2/resolve/%MODEL_VERSION%/config.json' -OutFile '%MODEL_DIR%\config.json'"

    echo   - Downloading vocab.json...
    powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/coqui/XTTS-v2/resolve/%MODEL_VERSION%/vocab.json' -OutFile '%MODEL_DIR%\vocab.json'"

    echo   - Downloading model.pth (this is a large file ~1.8GB)...
    powershell -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://huggingface.co/coqui/XTTS-v2/resolve/%MODEL_VERSION%/model.pth' -OutFile '%MODEL_DIR%\model.pth'"

    echo   - Downloading speakers_xtts.pth...
    powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/coqui/XTTS-v2/resolve/%MODEL_VERSION%/speakers_xtts.pth' -OutFile '%MODEL_DIR%\speakers_xtts.pth'"

    echo %GREEN%[SUCCESS]%NC% XTTS model files downloaded successfully
) else (
    echo %YELLOW%[WARNING]%NC% XTTS model files already exist, skipping download
)

echo.

:: =============================================================================
:: Sample Speakers
:: =============================================================================

echo %GREEN%[STEP]%NC% Checking sample speaker files...

set SAMPLE_URL=https://github.com/daswer123/xtts-api-server/raw/main/example

if not exist "speakers\calm_female.wav" (
    echo   - Downloading calm_female.wav...
    powershell -Command "Invoke-WebRequest -Uri '%SAMPLE_URL%/calm_female.wav' -OutFile 'speakers\calm_female.wav'"
)

if not exist "speakers\female.wav" (
    echo   - Downloading female.wav...
    powershell -Command "Invoke-WebRequest -Uri '%SAMPLE_URL%/female.wav' -OutFile 'speakers\female.wav'"
)

if not exist "speakers\male.wav" (
    echo   - Downloading male.wav...
    powershell -Command "Invoke-WebRequest -Uri '%SAMPLE_URL%/male.wav' -OutFile 'speakers\male.wav'"
)

echo %GREEN%[SUCCESS]%NC% Sample speakers ready

echo.

:: =============================================================================
:: Additional Setup
:: =============================================================================

echo %GREEN%[STEP]%NC% Running additional setup...

:: Download spacy model for Portuguese
python -m spacy download pt_core_news_sm 2>nul
if %errorlevel% neq 0 (
    echo %YELLOW%[WARNING]%NC% Failed to download spacy model (optional)
)

:: Run model downloader script if exists
if exist "scripts\modeldownloader.py" (
    python scripts\modeldownloader.py 2>nul
    if %errorlevel% neq 0 (
        echo %YELLOW%[WARNING]%NC% Model downloader script failed (optional)
    )
)

echo.

:: =============================================================================
:: Finish
:: =============================================================================

echo.
echo %GREEN%===============================================%NC%
echo %GREEN%  Installation Complete!%NC%
echo %GREEN%===============================================%NC%
echo.
echo To start the server:
echo.
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Run the server:
echo      python main.py
echo.
echo   3. Access the API documentation:
echo      http://localhost:8880/docs
echo.

pause
