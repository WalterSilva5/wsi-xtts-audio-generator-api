import torch

def gpu_is_available() -> bool:
    return torch.cuda.is_available()

def get_device():
    return torch.cuda.current_device()

def get_device_name() -> str:
    return torch.cuda.get_device_name(get_device())

def get_device_properties():
    return torch.cuda.get_device_properties(0)