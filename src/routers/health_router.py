"""Health check and system status endpoints."""
import platform
import psutil
import torch
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.modules.system.torch_util import gpu_is_available, get_gpu_type

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str = "1.0.0"


class SystemInfoResponse(BaseModel):
    """System information response model."""
    platform: str
    python_version: str
    cpu_count: int
    memory_total_gb: float
    memory_available_gb: float
    memory_percent_used: float
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_memory_free_gb: Optional[float] = None
    cuda_version: Optional[str] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the API is running and healthy."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/health/ready")
async def readiness_check():
    """Check if the API is ready to accept requests (model loaded)."""
    from src.tts.xtts.manager.tts_manager import TtsManager

    tts_manager = TtsManager()
    model_loaded = tts_manager.model.model_manager.is_loaded()

    if model_loaded:
        return {
            "status": "ready",
            "model_loaded": True,
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "status": "not_ready",
        "model_loaded": False,
        "message": "Model is not loaded yet",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/system", response_model=SystemInfoResponse)
async def system_info():
    """Get system information including GPU status."""
    memory = psutil.virtual_memory()
    gpu_type = get_gpu_type()
    is_gpu_available = gpu_is_available()

    info = SystemInfoResponse(
        platform=platform.system(),
        python_version=platform.python_version(),
        cpu_count=psutil.cpu_count(),
        memory_total_gb=round(memory.total / (1024**3), 2),
        memory_available_gb=round(memory.available / (1024**3), 2),
        memory_percent_used=memory.percent,
        gpu_available=is_gpu_available
    )

    if is_gpu_available:
        if gpu_type == "amd":
            info.gpu_name = "AMD GPU"
            info.cuda_version = torch.version.hip if hasattr(torch.version, 'hip') else "ROCm"
        else:
            info.gpu_name = torch.cuda.get_device_name(0)
            info.cuda_version = torch.version.cuda
            gpu_props = torch.cuda.get_device_properties(0)
            info.gpu_memory_total_gb = round(gpu_props.total_memory / (1024**3), 2)
            free_memory, total_memory = torch.cuda.mem_get_info(0)
            info.gpu_memory_free_gb = round(free_memory / (1024**3), 2)

    return info
