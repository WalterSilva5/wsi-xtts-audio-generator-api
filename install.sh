#!/bin/bash

# =============================================================================
# XTTS API - Installation Script (Linux/macOS)
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.10"
MODEL_VERSION="v2.0.3"
TORCH_VERSION="2.1.1"
CUDA_VERSION="cu118"
ROCM_VERSION="rocm7.1"
PYTORCH_INDEX_URL="https://download.pytorch.org/whl/${CUDA_VERSION}"
GPU_TYPE=""

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "  XTTS API - Installation Script"
    echo "=============================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

detect_gpu_type() {
    if command -v rocm-smi &> /dev/null; then
        echo "amd"
    elif command -v nvidia-smi &> /dev/null; then
        echo "nvidia"
    else
        echo "unknown"
    fi
}

select_gpu_type() {
    echo ""
    echo -e "${BLUE}=============================================="
    echo "  Select GPU Type"
    echo "==============================================${NC}"
    echo ""
    echo "Detected GPUs:"
    echo "  1) NVIDIA (CUDA)"
    echo "  2) AMD (ROCm)"
    echo ""
    echo -n "Select option [1-2]: "
    read -r choice

    case "$choice" in
        1) GPU_TYPE="nvidia" ;;
        2) GPU_TYPE="amd" ;;
        *) GPU_TYPE="nvidia" ;;
    esac

    echo -e "${GREEN}Selected: ${GPU_TYPE}${NC}"
    echo ""
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# =============================================================================
# Pre-requisites Check
# =============================================================================

print_header

print_step "Checking pre-requisites..."

# Check Python
check_command python3
PYTHON_INSTALLED=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "  - Python: $PYTHON_INSTALLED"

# Check pip
check_command pip3
echo "  - pip: $(pip3 --version | cut -d' ' -f2)"

# Check git
check_command git
echo "  - git: $(git --version | cut -d' ' -f3)"

# Check for wget or curl
if command -v wget &> /dev/null; then
    DOWNLOADER="wget"
    echo "  - wget: installed"
elif command -v curl &> /dev/null; then
    DOWNLOADER="curl"
    echo "  - curl: installed"
else
    print_error "Neither wget nor curl is installed. Please install one of them."
    exit 1
fi

# Check ffmpeg (optional but recommended)
if command -v ffmpeg &> /dev/null; then
    echo "  - ffmpeg: $(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f3)"
else
    print_warning "ffmpeg is not installed. Some audio features may not work."
fi

echo ""

# =============================================================================
# Virtual Environment
# =============================================================================

print_step "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

echo ""

# =============================================================================
# Dependencies
# =============================================================================

print_step "Installing Python dependencies..."

pip install -r requirements.txt

select_gpu_type

print_step "Installing PyTorch..."

if [ "$GPU_TYPE" = "amd" ]; then
    print_step "Installing PyTorch with ROCm ${ROCM_VERSION}..."
    pip install torch==${TORCH_VERSION} torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/${ROCM_VERSION}
    print_success "PyTorch with ROCm installed"
else
    print_step "Installing PyTorch with CUDA ${CUDA_VERSION}..."
    pip install torch==${TORCH_VERSION}+${CUDA_VERSION} torchaudio==${TORCH_VERSION}+${CUDA_VERSION} \
        --index-url https://download.pytorch.org/whl/${CUDA_VERSION}
    print_success "PyTorch with CUDA installed"
fi

echo ""

# =============================================================================
# Model Download
# =============================================================================

print_step "Checking XTTS model files..."

# Create directories
mkdir -p ./models/${MODEL_VERSION}
mkdir -p ./speakers

MODEL_DIR="./models/${MODEL_VERSION}"

download_file() {
    local url="$1"
    local output="$2"

    if [ "$DOWNLOADER" = "wget" ]; then
        wget -q --show-progress "$url" -O "$output"
    else
        curl -L --progress-bar "$url" -o "$output"
    fi
}

if [ ! -f "${MODEL_DIR}/config.json" ]; then
    print_step "Downloading XTTS model files (this may take a while)..."

    echo "  - Downloading config.json..."
    download_file "https://huggingface.co/coqui/XTTS-v2/resolve/${MODEL_VERSION}/config.json" "${MODEL_DIR}/config.json"

    echo "  - Downloading vocab.json..."
    download_file "https://huggingface.co/coqui/XTTS-v2/resolve/${MODEL_VERSION}/vocab.json" "${MODEL_DIR}/vocab.json"

    echo "  - Downloading model.pth (this is a large file ~1.8GB)..."
    download_file "https://huggingface.co/coqui/XTTS-v2/resolve/${MODEL_VERSION}/model.pth" "${MODEL_DIR}/model.pth"

    echo "  - Downloading speakers_xtts.pth..."
    download_file "https://huggingface.co/coqui/XTTS-v2/resolve/${MODEL_VERSION}/speakers_xtts.pth" "${MODEL_DIR}/speakers_xtts.pth"

    print_success "XTTS model files downloaded successfully"
else
    print_warning "XTTS model files already exist, skipping download"
fi

echo ""

# =============================================================================
# Sample Speakers
# =============================================================================

print_step "Checking sample speaker files..."

SAMPLE_URL="https://github.com/daswer123/xtts-api-server/raw/main/example"
SPEAKERS=("calm_female" "female" "male")

for speaker in "${SPEAKERS[@]}"; do
    if [ ! -f "./speakers/${speaker}.wav" ]; then
        echo "  - Downloading ${speaker}.wav..."
        download_file "${SAMPLE_URL}/${speaker}.wav" "./speakers/${speaker}.wav"
    fi
done

print_success "Sample speakers ready"

echo ""

# =============================================================================
# Additional Setup
# =============================================================================

print_step "Running additional setup..."

# Download spacy model for Portuguese
python -m spacy download pt_core_news_sm 2>/dev/null || print_warning "Failed to download spacy model (optional)"

# Run model downloader script if exists
if [ -f "scripts/modeldownloader.py" ]; then
    python scripts/modeldownloader.py 2>/dev/null || print_warning "Model downloader script failed (optional)"
fi

echo ""

# =============================================================================
# Finish
# =============================================================================

echo -e "${GREEN}"
echo "=============================================="
echo "  Installation Complete!"
echo "=============================================="
echo -e "${NC}"
echo ""
echo "To start the server:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run the server:"
echo "     python main.py"
echo ""
echo "  3. Access the API documentation:"
echo "     http://localhost:8880/docs"
echo ""
