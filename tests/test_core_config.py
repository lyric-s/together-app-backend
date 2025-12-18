import pytest
from unittest.mock import patch, MagicMock
from pydantic import HttpUrl, ValidationError

from app.core.config import Settings, get_settings


class TestSettings:
    """Test the Settings class."""

    def test_settings_creation_with_all_fields(self):
        """Test creating Settings with all required fields."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key-min-32-characters",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
        )
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
        assert settings.SECRET_KEY == "test-secret-key-min-32-characters"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.BACKEND_CORS_ORIGINS == []

    def test_settings_with_cors_origins(self):
        """Test Settings with CORS origins."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS=[
                "http://localhost:3000",
                "https://example.com"
            ],
        )
        assert len(settings.BACKEND_CORS_ORIGINS) == 2
        assert isinstance(settings.BACKEND_CORS_ORIGINS[0], HttpUrl)

    def test_settings_cors_origins_default_empty_list(self):
        """Test that CORS origins default to empty list."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
        )
        assert settings.BACKEND_CORS_ORIGINS == []

    def test_settings_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            Settings(
                # Missing DATABASE_URL and other required fields
                SECRET_KEY="test-secret-key",
            )

    def test_settings_database_url_formats(self):
        """Test various database URL formats."""
        # PostgreSQL
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/dbname",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
        )
        assert "postgresql://" in settings.DATABASE_URL

        # SQLite
        settings = Settings(
            DATABASE_URL="sqlite:///./test.db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
        )
        assert "sqlite:///" in settings.DATABASE_URL

    def test_settings_algorithm_validation(self):
        """Test that algorithm field accepts string values."""
        algorithms = ["HS256", "HS384", "HS512", "RS256"]
        for algo in algorithms:
            settings = Settings(
                DATABASE_URL="postgresql://user:pass@localhost/db",
                SECRET_KEY="test-secret-key",
                ALGORITHM=algo,
                ACCESS_TOKEN_EXPIRE_MINUTES=30,
                REFRESH_TOKEN_EXPIRE_DAYS=7,
            )
            assert settings.ALGORITHM == algo

    def test_settings_token_expiration_values(self):
        """Test various token expiration values."""
        # Short expiration
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=5,
            REFRESH_TOKEN_EXPIRE_DAYS=1,
        )
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 5
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 1

        # Long expiration
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=1440,  # 24 hours
            REFRESH_TOKEN_EXPIRE_DAYS=365,
        )
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 365

    def test_settings_secret_key_accepts_various_formats(self):
        """Test that secret key accepts various string formats."""
        secret_keys = [
            "simple-secret",
            "secret_with_underscores",
            "secret-with-dashes",
            "SecretWith123Numbers",
            "secret!@#$%^&*()",
            "a" * 100,  # Very long secret
        ]
        for secret in secret_keys:
            settings = Settings(
                DATABASE_URL="postgresql://user:pass@localhost/db",
                SECRET_KEY=secret,
                ALGORITHM="HS256",
                ACCESS_TOKEN_EXPIRE_MINUTES=30,
                REFRESH_TOKEN_EXPIRE_DAYS=7,
            )
            assert settings.SECRET_KEY == secret

    def test_settings_cors_origins_with_multiple_urls(self):
        """Test CORS origins with multiple URLs."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS=[
                "http://localhost:3000",
                "http://localhost:8080",
                "https://app.example.com",
                "https://api.example.com",
            ],
        )
        assert len(settings.BACKEND_CORS_ORIGINS) == 4

    def test_settings_cors_origins_validation(self):
        """Test that invalid URLs in CORS origins raise validation error."""
        with pytest.raises(ValidationError):
            Settings(
                DATABASE_URL="postgresql://user:pass@localhost/db",
                SECRET_KEY="test-secret-key",
                ALGORITHM="HS256",
                ACCESS_TOKEN_EXPIRE_MINUTES=30,
                REFRESH_TOKEN_EXPIRE_DAYS=7,
                BACKEND_CORS_ORIGINS=["not-a-valid-url"],
            )

    def test_settings_with_extra_fields_ignored(self):
        """Test that extra fields are ignored due to extra='ignore' config."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            UNKNOWN_FIELD="should be ignored",
        )
        assert not hasattr(settings, "UNKNOWN_FIELD")

    def test_settings_model_config(self):
        """Test that model_config is properly set."""
        assert Settings.model_config["env_file_encoding"] == "utf-8"
        assert Settings.model_config["env_file"] == ".env"
        assert Settings.model_config["extra"] == "ignore"


class TestGetSettings:
    """Test the get_settings function."""

    @patch.dict("os.environ", {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "SECRET_KEY": "env-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "45",
        "REFRESH_TOKEN_EXPIRE_DAYS": "14",
    })
    def test_get_settings_from_environment(self):
        """Test that get_settings reads from environment variables."""
        # Clear cache
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/testdb"
        assert settings.SECRET_KEY == "env-secret-key"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 45
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 14

    @patch.dict("os.environ", {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "SECRET_KEY": "env-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "45",
        "REFRESH_TOKEN_EXPIRE_DAYS": "14",
    })
    def test_get_settings_caching(self):
        """Test that get_settings uses LRU cache."""
        # Clear cache
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should return the same instance due to caching
        assert settings1 is settings2

    @patch.dict("os.environ", {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "SECRET_KEY": "env-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "45",
        "REFRESH_TOKEN_EXPIRE_DAYS": "14",
    })
    def test_get_settings_cache_clear(self):
        """Test that cache can be cleared."""
        get_settings.cache_clear()
        settings1 = get_settings()
        
        get_settings.cache_clear()
        settings2 = get_settings()
        
        # After cache clear, might get different instance
        # but should have same values
        assert settings1.DATABASE_URL == settings2.DATABASE_URL
        assert settings1.SECRET_KEY == settings2.SECRET_KEY

    @patch.dict("os.environ", {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "SECRET_KEY": "env-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        "BACKEND_CORS_ORIGINS": '["http://localhost:3000", "https://example.com"]',
    })
    def test_get_settings_with_cors_origins_from_env(self):
        """Test loading CORS origins from environment."""
        get_settings.cache_clear()
        
        settings = get_settings()
        assert len(settings.BACKEND_CORS_ORIGINS) == 2

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        get_settings.cache_clear()
        
        with patch.dict("os.environ", {
            "DATABASE_URL": "sqlite:///./test.db",
            "SECRET_KEY": "test-secret-key",
            "ALGORITHM": "HS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        }):
            settings = get_settings()
            assert isinstance(settings, Settings)

    def test_get_settings_has_lru_cache_decorator(self):
        """Test that get_settings has the lru_cache decorator."""
        assert hasattr(get_settings, "cache_clear")
        assert hasattr(get_settings, "cache_info")
        assert callable(get_settings.cache_clear)
        assert callable(get_settings.cache_info)


class TestSettingsEdgeCases:
    """Test edge cases for Settings."""

    def test_settings_with_zero_token_expiration(self):
        """Test settings with zero expiration values."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=0,
            REFRESH_TOKEN_EXPIRE_DAYS=0,
        )
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 0

    def test_settings_with_negative_token_expiration(self):
        """Test settings with negative expiration values."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=-10,
            REFRESH_TOKEN_EXPIRE_DAYS=-5,
        )
        # Pydantic allows negative integers by default
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == -10
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == -5

    def test_settings_with_very_large_expiration_values(self):
        """Test settings with very large expiration values."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=999999,
            REFRESH_TOKEN_EXPIRE_DAYS=999999,
        )
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 999999
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 999999

    def test_settings_database_url_with_special_characters(self):
        """Test database URL with special characters in password."""
        settings = Settings(
            DATABASE_URL="postgresql://user:p@ss!w0rd@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
        )
        assert "p@ss!w0rd" in settings.DATABASE_URL

    def test_settings_empty_cors_origins_list(self):
        """Test explicitly setting CORS origins to empty list."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS=[],
        )
        assert settings.BACKEND_CORS_ORIGINS == []
        assert isinstance(settings.BACKEND_CORS_ORIGINS, list)

    def test_settings_cors_origins_with_ports(self):
        """Test CORS origins with explicit ports."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS=[
                "http://localhost:3000",
                "http://localhost:8080",
                "https://example.com:443",
            ],
        )
        assert len(settings.BACKEND_CORS_ORIGINS) == 3

    def test_settings_cors_origins_with_paths(self):
        """Test CORS origins with paths."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            SECRET_KEY="test-secret-key",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS=[
                "http://localhost:3000/api",
                "https://example.com/app",
            ],
        )
        assert len(settings.BACKEND_CORS_ORIGINS) == 2