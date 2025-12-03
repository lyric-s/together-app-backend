from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    # Read the env file not present in the repo for security reasons,
    # overrides the attributes above based on the env file content
    model_config = SettingsConfigDict(env_file_encoding="utf-8", env_file=".env")


# Workaroud to avoid missing arguments warnings from :
# https://github.com/pydantic/pydantic/issues/3753#issuecomment-2516682968
settings = Settings.model_validate({})


def get_settings():
    """Get the useful settings/secrets from ENV variable"""
    return Settings.model_validate({})
