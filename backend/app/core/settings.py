from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool
    echo_sql: bool
    cors_origin: str
    database_url: str
    secret_key: str

    user_max_username_length: int
    user_max_email_length: int
    user_max_description_length: int

    club_max_name_length: int
    club_max_description_length: int

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# noinspection PyArgumentList
settings = Settings()  # type: ignore
