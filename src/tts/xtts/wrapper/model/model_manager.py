import os
from datetime import datetime
from typing import Optional, Dict, Any
import torch

from TTS.tts.configs.xtts_config import XttsConfig  # type: ignore
from TTS.tts.models.xtts import Xtts  # type: ignore
from src.core.application import Application
from src.tts.xtts.wrapper.model_wrapper_paths import ModelWrapperPaths

class XttsModelManager:
    """Responsible for managing the lifecycle of the XTTS model"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XttsModelManager, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.config = None
            cls._instance.using_gpu = False
            cls._instance.updated_at = None
            cls._instance.app = Application()
            cls._instance.model_paths = ModelWrapperPaths()
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'app'):
            self.app = Application()
            self.model_paths = ModelWrapperPaths()
            self.model = None
            self.config = None
            self.using_gpu = False
            self.updated_at = None

    def load_model(self) -> bool:
        try:
            print("Loading voice model")
            print(f"Loading voice model from {self.model_paths.model_folder}")

            if not self._verify_model_files():
                return False

            config = XttsConfig()
            config.load_json(self.model_paths.config_file)

            gpu_available = torch.cuda.is_available()
            if gpu_available:
                config.device = "cuda"
                self.using_gpu = True

            self.model = Xtts.init_from_config(config)
            # self.model.to("cuda")

            print("Loading XTTS model!")

            try:
                self.model.load_checkpoint(
                    config,
                    checkpoint_path=self.model_paths.model_file,
                    vocab_path=self.model_paths.vocab_file,
                    speaker_file_path=self.model_paths.speakers_file,
                    use_deepspeed=False
                )
            except Exception as e:
                if "weights_only" in str(e) or "WeightsUnpickler error" in str(e):
                    self.app.logger.warning(
                        "Model loading failed with weights_only=True, retrying with weights_only=False")
                    original_load = torch.load
                    torch.load = lambda *args, **kwargs: original_load(
                        *args, **{**kwargs, 'weights_only': False})
                    try:
                        self.model.load_checkpoint(
                            config,
                            checkpoint_path=self.model_paths.model_file,
                            vocab_path=self.model_paths.vocab_file,
                            speaker_file_path=self.model_paths.speakers_file,
                            use_deepspeed=False
                        )
                    finally:
                        # Restore original torch.load
                        torch.load = original_load
                else:
                    raise e
            self.config = config

            self.updated_at = datetime.now()
            print(f"Voice model loaded on device: {config.device}")

            return True
        except Exception as e:
            print(f"Error loading voice model: {e}")
            return False

    def unload_model(self) -> None:
        """Unloads the model from memory"""
        self.model = None
        del self.model
        print("Voice model unloaded")

    def get_model(self) -> Optional[Xtts]:
        """Returns the loaded model instance"""
        return self.model

    def get_info(self) -> Dict[str, Any]:
        """Returns information about the model state"""
        return {
            "model": self.model,
            "updated_at": self.updated_at,
            "using_gpu": self.using_gpu
        }

    def _verify_model_files(self) -> bool:
        """Verifies if all required model files exist"""
        if not os.path.exists(self.model_paths.model_folder):
            print(f"Model folder not found: {self.model_paths.model_folder}")
            return False

        if not os.path.exists(self.model_paths.config_file):
            print(f"Config file not found: {self.model_paths.config_file}")
            return False

        return True
