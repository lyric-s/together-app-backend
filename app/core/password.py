"""Password hashing utilities."""

from pwdlib import PasswordHash

# pwdlib is the modern, recommended way (Argon2 by default)
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plaintext password matches a stored hashed password.

    Returns:
        `True` if the plaintext password matches the hashed password, `False` otherwise.
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
