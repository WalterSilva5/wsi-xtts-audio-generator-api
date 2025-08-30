from src.observers.observable import Observable


class SingletonMeta(type):
    """
    Implements the singleton base class for all singletons in application
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ObservableSingletonMeta(SingletonMeta, type(Observable)):
    pass
