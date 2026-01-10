"""Password hashing utilities."""

import hashlib
from pwdlib import PasswordHash

# pwdlib is the modern, recommended way (Argon2 by default)
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check whether a plaintext password matches a stored hashed password.

    Returns:
        True if the plaintext password matches the hashed password, False otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using the recommended hashing algorithm (Argon2).

    Parameters:
        password (str): Plaintext password to hash.

    Returns:
        str: Password hash suitable for secure storage.
    """
    return password_hash.hash(password)


def get_token_hash(token: str) -> str:
    """
    Hash a token using SHA-256.

    Used for storing refresh tokens securely. SHA-256 is appropriate because tokens
    are high-entropy strings, unlike user passwords.

    Parameters:
        token (str): The token to hash.

    Returns:
        str: The SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, hashed_token: str) -> bool:
    """
    Verify a token against its stored hash.

    Parameters:
        token (str): The plaintext token to check.
        hashed_token (str): The stored SHA-256 hash.

    Returns:
        bool: True if the token matches the hash, False otherwise.
    """
    return get_token_hash(token) == hashed_token
