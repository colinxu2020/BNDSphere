from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool
    echo_sql: bool
    cors_origin: str
    database_url: str
    secret_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# noinspection PyArgumentList
settings = Settings()  # type: ignore[call-arg]
