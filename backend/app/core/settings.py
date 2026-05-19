from functools import cache
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _AppBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir="/run/secrets")


class WebSettings(_AppBaseSettings):
    debug: bool
    cors_origin: str
    secret_key: str


class DatabaseSettings(_AppBaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        safe_password = quote_plus(self.postgres_password)

        return f"postgresql+psycopg://{self.postgres_user}:{safe_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(secrets_dir="/run/secrets")


@cache
def db_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


@cache
def web_settings() -> WebSettings:
    return WebSettings()  # type: ignore[call-arg]
