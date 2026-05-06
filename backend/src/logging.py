import logging
import sys
from datetime import datetime
from logging.config import dictConfig
from typing import Any, Final
from zoneinfo import ZoneInfo

from src.settings import settings
from src.shared.enums import LogLevelEnum

__all__ = ['setup_logger', 'get_logging_config']


class LineFormatter(logging.Formatter):
    """Line formatter для development логов."""

    LEVEL_WIDTH = 8

    def __init__(self) -> None:
        super().__init__()
        self._tz = ZoneInfo(settings.app.tz)

    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует лог-запись в строковый формат.

        :param record: Лог-запись
        :return: Строка с данными лога
        """
        timestamp = self._format_time(record)
        level = self._format_level(record.levelname)
        message = self._format_message(record)
        location = self._format_location(record)

        log_line = f'{timestamp} | {level} | {message} {location}'

        if record.exc_info:
            log_line += '\n' + self.formatException(record.exc_info)

        return log_line

    def _format_time(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created, tz=self._tz)
        return dt.isoformat()

    def _format_level(self, level: str) -> str:
        return level.ljust(self.LEVEL_WIDTH)

    def _format_message(self, record: logging.LogRecord) -> str:
        return record.getMessage()

    def _format_location(self, record: logging.LogRecord) -> str:
        return f'({record.name}:{record.funcName}:{record.lineno})'


class ColoredLineFormatter(LineFormatter):
    """Цветной line formatter для development логов."""

    GREEN = '\033[32m'
    GRAY = '\033[90m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'

    COLORS: Final[dict[str, str]] = {
        LogLevelEnum.DEBUG: CYAN,
        LogLevelEnum.INFO: WHITE,
        LogLevelEnum.WARNING: YELLOW,
        LogLevelEnum.ERROR: RED,
        LogLevelEnum.CRITICAL: MAGENTA,
    }

    def _format_time(self, record: logging.LogRecord) -> str:
        time = super()._format_time(record)
        return f'{self.GREEN}{time}{self.RESET}'

    def _format_level(self, level: str) -> str:
        base = super()._format_level(level)
        color = self.COLORS.get(level, self.RESET)
        return f'{color}{base}{self.RESET}'

    def _format_message(self, record: logging.LogRecord) -> str:
        message = super()._format_message(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f'{color}{message}{self.RESET}'

    def _format_location(self, record: logging.LogRecord) -> str:
        location = super()._format_location(record)
        return f'{self.GRAY}{location}{self.RESET}'


def get_logging_config() -> dict[str, Any]:
    """
    Создает конфигурацию логирования в зависимости от окружения.

    :return: Словарь конфигурации для logging.config.dictConfig
    """
    if sys.stdout.isatty():
        formatter_class = 'src.logging.ColoredLineFormatter'
    else:
        formatter_class = 'src.logging.LineFormatter'

    log_level = settings.log.level.value.upper()

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                '()': formatter_class,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'src': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
            'uvicorn': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
            'uvicorn.access': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
            'uvicorn.error': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
            'fastapi': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': log_level,
        },
    }


def setup_logger() -> None:
    """
    Инициализирует систему логирования.
    Применяет конфигурацию в зависимости от окружения (production/development).
    """
    config = get_logging_config()
    dictConfig(config)
