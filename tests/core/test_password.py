"""Tests for password hashing and verification utilities."""

import hashlib
from app.core.password import (
    get_password_hash,
    verify_password,
    get_token_hash,
    verify_token,
)

# Test constants
TEST_PASSWORD = "Password123!"
TEST_WRONG_PASSWORD = "WrongPassword123"
TEST_TOKEN = "test-token-value-12345"
TEST_WRONG_TOKEN = "wrong-token-value"
TEST_SPECIAL_PASSWORD = "P@ssw0rd!#$%^&*()"
TEST_UNICODE_PASSWORD = "Pāsswörd123🔒"
TEST_LONG_PASSWORD = "A" * 1000


class TestPasswordHashing:
    """Test password hashing functions using Argon2 via pwdlib."""

    def test_get_password_hash_returns_string(self):
        """Verify that get_password_hash returns a non-empty string."""
        hashed = get_password_hash(TEST_PASSWORD)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_is_unique(self):
        """Verify that each hash is unique due to default Argon2 salting."""
        hash1 = get_password_hash(TEST_PASSWORD)
        hash2 = get_password_hash(TEST_PASSWORD)
        assert hash1 != hash2

    def test_verify_password_success(self):
        """Verify that a correct password matches its hash."""
        hashed = get_password_hash(TEST_PASSWORD)
        assert verify_password(TEST_PASSWORD, hashed) is True

    def test_verify_password_failure(self):
        """Verify that an incorrect password does not match the hash."""
        hashed = get_password_hash(TEST_PASSWORD)
        assert verify_password(TEST_WRONG_PASSWORD, hashed) is False

    def test_verify_empty_password(self):
        """Verify that an empty password does not match a valid hash."""
        hashed = get_password_hash(TEST_PASSWORD)
        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Verify hashing and verification of passwords with special characters."""
        hashed = get_password_hash(TEST_SPECIAL_PASSWORD)
        assert verify_password(TEST_SPECIAL_PASSWORD, hashed) is True

    def test_hash_unicode_characters(self):
        """Verify hashing and verification of passwords with unicode characters."""
        hashed = get_password_hash(TEST_UNICODE_PASSWORD)
        assert verify_password(TEST_UNICODE_PASSWORD, hashed) is True

    def test_hash_very_long_password(self):
        """Verify hashing and verification of very long passwords."""
        hashed = get_password_hash(TEST_LONG_PASSWORD)
        assert verify_password(TEST_LONG_PASSWORD, hashed) is True


class TestTokenHashing:
    """Test token hashing functions using deterministic SHA-256."""

    def test_get_token_hash_deterministic(self):
        """Verify that get_token_hash is deterministic (same input produces same hash)."""
        expected_hash = hashlib.sha256(TEST_TOKEN.encode()).hexdigest()
        hashed = get_token_hash(TEST_TOKEN)

        assert hashed == expected_hash
        assert get_token_hash(TEST_TOKEN) == get_token_hash(TEST_TOKEN)

    def test_verify_token_success(self):
        """Verify that a correct token matches its stored SHA-256 hash."""
        hashed = get_token_hash(TEST_TOKEN)
        assert verify_token(TEST_TOKEN, hashed) is True

    def test_verify_token_failure(self):
        """Verify that an incorrect token does not match the hash."""
        hashed = get_token_hash(TEST_TOKEN)
        assert verify_token(TEST_WRONG_TOKEN, hashed) is False

    def test_verify_token_empty(self):
        """Verify that an empty token does not match a valid token's hash."""
        hashed = get_token_hash(TEST_TOKEN)
        assert verify_token("", hashed) is False
