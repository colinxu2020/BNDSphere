from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool
    cors_origin: str
    database_url: str
    secret_key: str
    max_username_length: int
    max_email_length: int
    max_description_length: int
    echo_sql: bool

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# noinspection PyArgumentList
settings = Settings()  # type: ignore
