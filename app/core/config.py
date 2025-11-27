from functools import lru_cache

@lru_cache
def get_settings():
    """Get the useful settings/secrets from ENV variable"""
    return Settings()