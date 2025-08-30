import os

def get_process_id() -> int:
    return os.getpid() or 1

def get_cpu_count() -> int:
    return os.cpu_count() or 1