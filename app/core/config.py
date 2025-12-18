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


@lru_cache()
# get_settings.cach_clear() may be needed for tests that modify env vars
def get_settings():
    """
    Load application settings from environment variables and the configured .env file.

    This function is cached, so repeated calls return the same Settings instance until the cache is cleared.

    Returns:
        Settings: A Settings instance populated from environment variables and the `.env` file according to the model configuration.
    """
    return Settings()
