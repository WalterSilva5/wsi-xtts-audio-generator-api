import numpy as np
from typing import Any, List, Optional, Dict
from src.tts.xtts.wrapper.audio.audio_synthesizer import AudioSynthesizer
from src.tts.xtts.wrapper.types.speaker_embedding_type import SpeakerEmbedding
from src.tts.xtts.dto.tts_dto import TtsDto
from src.tts.xtts.wrapper.speaker_embedding import SpeakerEmbeddingFactory, SpeakerEmbeddingManager
from src.tts.xtts.wrapper.model.model_manager import XttsModelManager
from src.observers.observable import Observable
from src.core.application import Application

class ModelWrapper(Observable):
    """
    Facade for the XTTS model system. Maintains backward compatibility while delegating
    to specialized components.
    """
    embedding_manager: Optional[SpeakerEmbeddingManager] = None
    _audio_synthesizer: Optional[AudioSynthesizer] = None

    def __init__(self):
        super().__init__()
        self.app = Application()
        self.model_manager = XttsModelManager()
        self.embedding_manager: Optional[SpeakerEmbeddingManager] = None
        self._audio_synthesizer = None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ModelWrapper, cls).__new__(cls)
        return cls.instance

    @property
    def speaker_embeddings(self) -> Dict[str, SpeakerEmbedding]:
        if self.embedding_manager is None:
            return {}
        return self.embedding_manager.get_all_embeddings()

    def load_model(self)-> bool:
        """Loads the model and initializes all components"""
        if not self.model_manager.load_model():
            return False
        self.embedding_manager = SpeakerEmbeddingFactory.create_manager(
            "default",
            self.model_manager.get_model(),
            self.model_manager.model_paths
        )
        self.embedding_manager.load_embeddings()

        self._audio_synthesizer = AudioSynthesizer(
            self.model_manager,
            self.embedding_manager
        )

        return True

    def unload_model(self) -> None:
        """Unloads the model and cleans up resources"""
        self.model_manager.unload_model()
        self.embedding_manager = None
        self._audio_synthesizer = None

    def info(self) -> Dict[str, Any]:
        """Returns information about the model state"""
        return self.model_manager.get_info()

    def list_speakers(self) -> List[str]:
        """Lists available speakers"""
        if self.embedding_manager is None:
            self.app.logger.warning("Embedding manager not initialized")
            return []
        return self.embedding_manager.list_speakers()

    def synthesize_audio(self, dto: TtsDto) -> np.ndarray:
        """Synthesizes audio from text"""
        return self._audio_synthesizer.synthesize(dto)

    def reload_all_speaker_embeddings(self) -> None:
        """Reloads all speaker embeddings"""
        if self.embedding_manager:
            self.embedding_manager.load_embeddings()
