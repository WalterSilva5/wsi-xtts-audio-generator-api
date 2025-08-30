import ctypes
import gc
import logging
import sys

logger = logging.getLogger(__name__)

def cleanup_memory():
    """
    Clean up memory by performing garbage collection, freeing unused memory, and flushing output buffers.

    This function collects garbage using the `gc.collect()` method, logs the number of uncollectable objects,
    attempts to free memory using the `malloc_trim()` function from the `libc` library, and flushes the output
    buffers for `sys.stdout` and `sys.stderr`. It also logs the success or failure of the memory trimming operation.

    Note: This function may raise exceptions if there are errors during the memory cleanup process.

    Returns:
        None
    """
    gc.collect()
    logger.info("Limpando %d objetos não coletáveis.", len(gc.garbage))

    try:
        libc = ctypes.CDLL("libc.so.6")
        result = libc.malloc_trim(0)
        if result:
            logger.info("malloc_trim executado com sucesso.")
        else:
            logger.warning("malloc_trim executado, mas sem liberação de memória.")
    except (OSError, AttributeError, Exception) as e:
        logger.warning("Não foi possível executar malloc_trim: %s", e)

    sys.stdout.flush()
    sys.stderr.flush()
    logger.info("Buffers de saída limpos.")

