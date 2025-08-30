from src.core.application import Application
from src.tts.xtts.wrapper.paths.base_paths import ModelPaths, CoreModelPathProvider, SpeakerPathProvider

class ModelWrapperPaths:
    """Facade for backward compatibility with existing code"""
    model_folder: str
    config_file: str
    vocab_file: str
    model_file: str
    speakers_file: str
    speakers_dir_path: str
    app: Application

    def __init__(self):
        self.app = Application()
        
        # Initialize new path providers
        self._model_paths = ModelPaths(app=self.app, base_folder="")
        self._core_provider = CoreModelPathProvider(self._model_paths)
        self._speaker_provider = SpeakerPathProvider(self._model_paths)

        # Maintain backward compatibility by setting the old properties
        self.model_folder = self._model_paths.base_folder
        self.config_file = self._core_provider.get_config_file()
        self.vocab_file = self._core_provider.get_vocab_file()
        self.model_file = self._core_provider.get_model_file()
        self.speakers_file = self._speaker_provider.get_speakers_file()
        self.speakers_dir_path = self._speaker_provider.get_speakers_dir()
