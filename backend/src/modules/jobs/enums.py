from enum import auto

from src.shared.enums import UpperCaseEnum


class JobStatus(UpperCaseEnum):
    """Статус задачи обработки графа."""

    PENDING = auto()
    PROCESSING = auto()
    GRAPH_BUILDING = auto()
    DETECTING = auto()
    SCORING = auto()
    LAYOUT = auto()
    SAVING = auto()
    COMPLETED = auto()
    FAILED = auto()


class UploadFormat(UpperCaseEnum):
    """Формат загружаемого файла транзакций."""

    IBM = auto()
    CUSTOM = auto()
