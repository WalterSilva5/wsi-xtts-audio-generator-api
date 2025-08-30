import logging
import asyncio

from src.modules.meta.observable_singleton import ObservableSingletonMeta
from src.observers.observable import Observable
from src.core.environment_variables import environment_variables

class Application(Observable, metaclass=ObservableSingletonMeta):
    event_loop = asyncio.get_event_loop()

    def __init__(self):
        super().__init__()
        self.initialize_logger()

    envs = environment_variables

    def initialize_logger(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
        self.logger = logging.getLogger("application")
