from typing import TypeVar
from app.exceptions import AppException

T = TypeVar("T")


def ensure_id(id_value: T | None, resource_name: str = "Resource") -> T:
    """
    Ensure that an ID value is not None.

    Args:
        id_value: The ID value to check.
        resource_name: The name of the resource for the error message.

    Returns:
        The non-None ID value.

    Raises:
        AppException: If the ID value is None.
    """
    if id_value is None:
        raise AppException(f"{resource_name} ID is missing")
    return id_value


def mask_email(email: str) -> str:
    """
    Mask an email address for safe logging.
    Example: 'user@example.com' -> 'u***r@example.com'
    """
    try:
        user_part, domain = email.split("@")
        if len(user_part) <= 2:
            return f"{user_part[0]}***@{domain}"
        return f"{user_part[0]}***{user_part[-1]}@{domain}"
    except Exception:
        return "***@***.***"
