from src.tts.xtts.wrapper.model_wrapper import ModelWrapper
from src.observers.observable import Observable


class TtsManager(Observable):
    """
        Singleton class that manages the voice models.
    """
    _instance = None
    model: ModelWrapper = ModelWrapper()
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.model = ModelWrapper()
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            super().__init__()
            self.initialized = True

    @classmethod
    def get_instance(cls):
        """Returns the singleton instance of the TtsManager."""
        if cls._instance is None:
            cls._instance = TtsManager()
        return cls._instance
