from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class DatabaseSettings(BaseModel):
    """Параметры подключения к PostgreSQL.

    Attributes:
        host: Имя хоста или IP-адрес сервера.
        port: Порт сервера PostgreSQL.
        name: Имя базы данных приложения.
        user: Имя пользователя базы данных.
        password: Пароль пользователя, если задан.
        pool_size: Максимальное число соединений в пуле на процесс приложения.
    """

    host: str = "127.0.0.1"
    port: int = Field(default=5433, ge=1, le=65535)
    name: str = "ai_task_planner"
    user: str = "planner"
    password: SecretStr | None = None
    pool_size: int = Field(default=5, ge=1)


class KeycloakSettings(BaseModel):
    """Параметры подключения к Keycloak по OIDC.

    Attributes:
        url: Базовый URL сервера Keycloak.
        realm: Имя области (realm), в которой зарегистрирован клиент.
        client_id: Идентификатор клиента OIDC.
        client_secret: Секрет клиента, используемого для проверки токенов.
        admin_client_id: Идентификатор сервисного клиента для регистрации.
        admin_client_secret: Секрет сервисного клиента.
    """

    url: HttpUrl = HttpUrl("http://127.0.0.1:8080")
    realm: str | None = None
    client_id: str | None = None
    client_secret: SecretStr | None = None
    admin_client_id: str | None = None
    admin_client_secret: SecretStr | None = None


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения и файла .env.

    Переменные окружения имеют приоритет над значениями из файла.

    Attributes:
        database: Параметры PostgreSQL из переменных с префиксом DATABASE__.
        keycloak: Параметры Keycloak из переменных с префиксом KEYCLOAK__.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        extra="ignore",
    )

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    keycloak: KeycloakSettings = Field(default_factory=KeycloakSettings)
