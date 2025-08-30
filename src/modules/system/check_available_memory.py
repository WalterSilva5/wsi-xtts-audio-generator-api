import psutil  # type: ignore

import logging

logger = logging.getLogger("uvicorn")


import psutil

def check_available_memory():
    """
    Check the available memory in the system.

    Returns:
        bool: True if the available memory is greater than or equal to 1.3 GB, False otherwise.
    """
    available_memory = psutil.virtual_memory().available
    available_memory_gb = available_memory / (1024 ** 3)
    logger.info("Available memory: %s GB", available_memory_gb)

    return available_memory_gb >= 1.3
