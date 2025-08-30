from abc import ABC
from typing import Any, List
from src.observers.observer import Observer


class Observable(ABC):

    def __init__(self):
        self._observers: List[Observer] = []

    def add_observer(self, observer: Observer) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify_observers(self, event: Any) -> None:
        for observer in self._observers:
            observer.update(event)
