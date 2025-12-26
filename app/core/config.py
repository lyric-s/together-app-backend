from pydantic.types import SecretStr
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import HttpUrl


def parse_comma_separated_origins(comma_list: str) -> list[HttpUrl]:
    """
    Parse a comma-separated string into a list of validated HttpUrl origins.

    Empty or falsy input returns an empty list. Each non-empty, comma-separated item is validated and converted to an HttpUrl.

    Parameters:
        comma_list (str): Comma-separated origins (may be empty or falsy).

    Returns:
        list[HttpUrl]: A list of parsed and validated HttpUrl objects.

    Raises:
        ValueError: If any origin cannot be parsed as an HttpUrl; the error message includes the invalid origin and the underlying reason.
    """
    if not comma_list:
        return []
    # Split by comma and strip whitespace
    origins = []
    for origin in comma_list.split(","):
        origin = origin.strip()
        if origin:
            try:
                origins.append(HttpUrl(origin))
            except Exception as e:
                raise ValueError(f"Invalid CORS origin '{origin}': {e}") from e
    return origins


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: SecretStr
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    BACKEND_CORS_ORIGINS: str
    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: SecretStr
    FIRST_SUPERUSER_USERNAME: str = "superadmin"
    ENVIRONMENT: str
    UPLOADS_BUCKET: str
    AVATARS_BUCKET: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

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
