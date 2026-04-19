import os
import torch
from settings.environment_variables import environment_variables


def get_gpu_type() -> str:
    gpu_type = environment_variables.GPU_TYPE if environment_variables.GPU_TYPE else os.environ.get("GPU_TYPE", "")
    if gpu_type:
        return gpu_type.lower()

    if hasattr(torch.version, 'hip') and torch.version.hip:
        return "amd"

    if torch.cuda.is_available():
        return "nvidia"

    return "unknown"


def gpu_is_available() -> bool:
    try:
        return torch.cuda.is_available()
    except Exception:
        return False


def get_device():
    return 0


def get_device_name() -> str:
    try:
        return torch.cuda.get_device_name(0)
    except Exception:
        gpu_type = get_gpu_type()
        return "AMD GPU" if gpu_type == "amd" else "Unknown GPU"


def get_device_properties():
    try:
        return torch.cuda.get_device_properties(0)
    except Exception:
        return None


def get_device_total_memory() -> int:
    try:
        props = torch.cuda.get_device_properties(0)
        return props.total_memory
    except Exception:
        return 0


def get_device_free_memory() -> int:
    try:
        free, _ = torch.cuda.mem_get_info(0)
        return free
    except Exception:
        return 0


def empty_cache():
    try:
        torch.cuda.empty_cache()
    except Exception:
        pass


def synchronize():
    try:
        torch.cuda.synchronize()
    except Exception:
        pass