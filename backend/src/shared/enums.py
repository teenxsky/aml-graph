from enum import StrEnum, auto


class UpperCaseEnum(StrEnum):
    """Enum со значениями в uppercase."""

    @staticmethod
    def _generate_next_value_(
        name: str,
        start: int,
        count: int,
        last_values: list[str],
    ) -> str:
        return name.upper()


class LogLevelEnum(UpperCaseEnum):
    """Enum для уровня логирования приложения."""

    CRITICAL = auto()
    NOTSET = auto()
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    FATAL = auto()
