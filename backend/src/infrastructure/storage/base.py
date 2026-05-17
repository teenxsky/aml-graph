from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """Базовый интерфейс файлового хранилища."""

    @abstractmethod
    def __init__(self, base_path: str) -> None: ...
