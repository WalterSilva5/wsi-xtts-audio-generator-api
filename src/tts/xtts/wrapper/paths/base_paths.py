from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.core.application import Application

class ModelPathProvider(ABC):
    @abstractmethod
    def get_path(self) -> str:
        """Returns the base path for this provider"""
        pass

@dataclass
class ModelPaths:
    """Base class for model related paths"""
    app: Application
    base_folder: str

    def __post_init__(self):
        self.app = Application()
        self.base_folder = f"{self.app.envs.XTTS_MODEL_FOLDER}{self.app.envs.MODEL_FOLDER}"

class CoreModelPathProvider(ModelPathProvider):
    """Provides paths for core model files"""
    def __init__(self, paths: ModelPaths):
        self.paths = paths

    def get_path(self) -> str:
        """Returns the base path for core model files"""
        return self.paths.base_folder

    def get_model_file(self) -> str:
        return f"{self.paths.base_folder}{self.paths.app.envs.MODEL_FILE}"

    def get_config_file(self) -> str:
        return f"{self.paths.base_folder}{self.paths.app.envs.CONFIG_FILE}"
    
    def get_vocab_file(self) -> str:
        return f"{self.paths.base_folder}{self.paths.app.envs.VOCAB_FILE}"

class SpeakerPathProvider(ModelPathProvider):
    """Provides paths for speaker related files"""
    def __init__(self, paths: ModelPaths):
        self.paths = paths

    def get_path(self) -> str:
        """Returns the base path for speaker files"""
        return self.paths.app.envs.XTTS_MODEL_FOLDER

    def get_speakers_file(self) -> str:
        return f"{self.paths.base_folder}{self.paths.app.envs.SPEAKERS_FILE}"
    
    def get_speakers_dir(self) -> str:
        return f"{self.paths.app.envs.XTTS_MODEL_FOLDER}{self.paths.app.envs.MODEL_FOLDER}{self.paths.app.envs.SAMPLE_SPEAKERS_FOLDER}"