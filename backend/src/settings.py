from pydantic import Field
from pydantic_settings import BaseSettings as _BaseSettings
from pydantic_settings import SettingsConfigDict

from src.shared.enums import LogLevelEnum

__all__ = ['settings']


# ================= Base Settings =================


class BaseSettings(_BaseSettings):
    """Базовый класс для всех конфигураций."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )


# ================= Settings Implementations =================


class AppSettings(BaseSettings, env_prefix='APP_'):
    """Базовая конфигурация приложения."""

    name: str = Field(
        default='scoring-web',
        description='Название приложения (используется в логах и метриках)',
    )
    host: str = Field(
        default='127.0.0.1',
        description='Хост, на котором запускается приложение',
    )
    port: int = Field(
        default=9090,
        description='Порт, на котором запускается приложение',
        ge=1,
        le=65535,
    )
    debug: bool = Field(
        default=False,
        description='Флаг включения режима отладки',
    )
    tz: str = Field(
        default='Asia/Vladivostok',
        description='Часовой пояс приложения',
    )


class LogSettings(BaseSettings, env_prefix='LOG_'):
    """Конфигурация логирования."""

    level: LogLevelEnum = Field(
        default=LogLevelEnum.INFO,
        description='Уровень логирования приложения',
    )


class HTTPSettings(BaseSettings, env_prefix='HTTP_'):
    """Конфигурация HTTP-сервера и служебных эндпоинтов."""

    docs_path: str = Field(
        default='/docs',
        description='HTTP-путь для документации API',
    )


class Settings(BaseSettings):
    """Главный контейнер конфигурации приложения."""

    app: AppSettings = Field(default_factory=AppSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    http: HTTPSettings = Field(default_factory=HTTPSettings)


settings = Settings()
