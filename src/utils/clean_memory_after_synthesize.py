import gc
import ctypes
from src.core.application import Application

app = Application()

def cleanup_memory_after_synthesize():
    try:
        collected = gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            app.logger.info("PyTorch not installed. Skipping PyTorch memory cleanup.")
        except Exception as e:
            app.logger.info(f"Error during PyTorch memory cleanup: {e}")

        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception as e:
            app.logger.info("malloc_trim not executed or not available on this system.")

    except Exception as e:
        app.logger.info(f"Error during general memory cleanup: {e}")
