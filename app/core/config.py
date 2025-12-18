from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import HttpUrl


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    BACKEND_CORS_ORIGINS: list[HttpUrl] = []
    # Read the env file not present in the repo for security reasons,
    # overrides the attributes above based on the env file content
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8", env_file=".env", extra="ignore"
    )


@lru_cache
def get_settings():
    """Get the useful settings/secrets from ENV variable"""
    return Settings()
