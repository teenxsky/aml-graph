from enum import StrEnum, auto


class LogLevelEnum(StrEnum):
    """Enum для уровня логирования приложения."""

    @staticmethod
    def _generate_next_value_(
        name: str,
        start: int,
        count: int,
        last_values: list[str],
    ) -> str:
        return name.upper()

    CRITICAL = auto()
    NOTSET = auto()
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()
