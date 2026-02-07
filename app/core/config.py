from typing import Literal
from pydantic.types import SecretStr
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import HttpUrl


def parse_comma_separated_origins(comma_list: str) -> list[str]:
    """
    Parse a comma-separated string into a list of validated CORS origins.

    CORS origins follow the format `scheme://host[:port]` with NO path component,
    unlike full URLs. This function validates each origin using Pydantic's HttpUrl
    for format checking, then returns clean strings without trailing slashes.

    Empty or falsy input returns an empty list. Each non-empty, comma-separated
    item is validated and converted to a properly formatted origin string.

    Parameters:
        comma_list (str): Comma-separated origins (may be empty or falsy).

    Returns:
        list[str]: A list of validated origin strings without trailing slashes.

    Raises:
        ValueError: If any origin cannot be parsed as a valid HTTP/HTTPS URL;
                   the error message includes the invalid origin and the underlying reason.

    Example:
        >>> parse_comma_separated_origins("http://localhost:3000, https://example.com")
        ['http://localhost:3000', 'https://example.com']
    """
    if not comma_list:
        return []
    # Split by comma and strip whitespace
    origins = []
    for origin in comma_list.split(","):
        origin = origin.strip()
        if origin:
            try:
                # Validate using HttpUrl, then convert to string without trailing slash
                validated = HttpUrl(origin)
                origins.append(str(validated).rstrip("/"))
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
    ENVIRONMENT: Literal["development", "staging", "production"]
    DOCUMENTS_BUCKET: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: SecretStr
    MINIO_SECRET_KEY: SecretStr
    MINIO_SECURE: bool
    MAX_UPLOAD_SIZE_MB: int = 100
    # Email settings (optional - required only for password reset feature)
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "Together Platform"
    FRONTEND_URL: str | None = None
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # AI Moderation Service Settings
    AI_SPAM_MODEL_URL: HttpUrl | None = None
    AI_TOXICITY_MODEL_URL: HttpUrl | None = None
    AI_MODERATION_SERVICE_TOKEN: SecretStr | None = None
    AI_MODERATION_DAILY_QUOTA: int = 100  # Default daily quota for AI calls
    AI_MODERATION_TIMEOUT_SECONDS: int = 5  # Default timeout for AI service calls
    AI_MODEL_VERSION: str = "CamemBERT-v1.0" # Default AI model version

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
