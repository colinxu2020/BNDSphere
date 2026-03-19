from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    cors_origin: str = '*'

    model_config = SettingsConfigDict(
        env_file = '.env',
        env_file_encoding = 'utf-8'
    )

settings = Settings()