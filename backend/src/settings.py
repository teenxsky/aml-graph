from pydantic import AmqpDsn, Field, PostgresDsn, RedisDsn
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


class BasePgsqlDatabaseSettings(BaseSettings):
    host: str = Field(description='Хост базы данных')
    port: int = Field(description='Порт базы данных')
    database: str = Field(description='Имя базы данных')
    user: str = Field(description='Пользователь базы данных')
    password: str = Field(description='Пароль пользователя базы данных')

    pool_size: int = Field(description='Размер пула для подключения к БД')
    max_pool_size: int = Field(
        description='Максимальный допустимый размер пула для подключения к БД',
    )

    @property
    def sync_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme='postgresql+psycopg',
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            path=self.database,
        )

    @property
    def async_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            path=self.database,
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


class RabbitMQSettings(BaseSettings, env_prefix='RABBITMQ_'):
    """Конфигурация подключения к RabbitMQ."""

    host: str = Field(
        default='localhost',
        description='Хост RabbitMQ',
    )
    vhost: str = Field(
        default='/',
        description='Virtual host RabbitMQ',
    )
    port: int = Field(
        default=5672,
        description='Порт RabbitMQ',
        ge=1,
        le=65535,
    )
    user: str = Field(
        description='Имя пользователя RabbitMQ',
    )
    password: str = Field(
        description='Пароль пользователя RabbitMQ',
    )
    mbws_exchange: str = Field(
        description='Имя exchange для приложения',
    )

    @property
    def dsn(self) -> AmqpDsn:
        """DSN для подключения к RabbitMQ."""
        return AmqpDsn.build(
            scheme='amqp',
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            path=self.vhost,
        )


class AMLDatabaseSettings(BasePgsqlDatabaseSettings, env_prefix='AML_DB_'):
    """Конфигурация базы данных AML."""


class LadybugSettings(BaseSettings, env_prefix='LADYBUG_'):
    """Конфигурация файлового хранилища LadybugDB."""

    db_path: str = Field(
        default='/var/lib/ladybug',
        description='Директория для .lbug файлов (монтируется как Docker volume)',
    )


class RedisSettings(BaseSettings, env_prefix='REDIS_'):
    """Конфигурация Redis (result backend для taskiq pipelines)."""

    host: str = Field(default='redis', description='Хост Redis')
    port: int = Field(default=6379, description='Порт Redis', ge=1, le=65535)
    db: int = Field(default=0, description='Номер базы данных Redis')

    @property
    def dsn(self) -> RedisDsn:
        return RedisDsn.build(
            scheme='redis',
            host=self.host,
            port=self.port,
            path=str(self.db),
        )


class StorageSettings(BaseSettings, env_prefix='STORAGE_'):
    """Конфигурация хранилища загруженных CSV файлов."""

    csv_path: str = Field(
        default='/var/lib/aml/uploads',
        description='Директория для загруженных CSV файлов',
    )


class ClusteringSettings(BaseSettings, env_prefix='CLUSTERING_'):
    """Конфигурация кластеризации и иерархического layout."""

    random_state: int = Field(
        default=42,
        description='Seed для воспроизводимости AGC/Louvain/KMeans/spring_layout',
    )
    agc_max_k: int = Field(
        default=60,
        description='Максимальный порядок фильтра для алгоритма AGC',
        ge=1,
    )
    cluster_radius_factor: float = Field(
        default=0.15,
        description='Множитель радиуса внутрикластерного layout (radius = sqrt(n) * factor)',
        gt=0.0,
    )


class Settings(BaseSettings):
    """Главный контейнер конфигурации приложения."""

    app: AppSettings = Field(default_factory=AppSettings)
    log: LogSettings = Field(default_factory=LogSettings)
    http: HTTPSettings = Field(default_factory=HTTPSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    aml_db: AMLDatabaseSettings = Field(default_factory=AMLDatabaseSettings)
    ladybug: LadybugSettings = Field(default_factory=LadybugSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    clustering: ClusteringSettings = Field(default_factory=ClusteringSettings)


settings = Settings()
