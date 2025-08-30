from abc import ABC, abstractmethod
from typing import Any


class Observer(ABC):

    @abstractmethod
    def update(self, event: Any) -> None:
        """Receive an update from the observable."""
        pass
