"""
Application exceptions module.

This module provides a clean separation of concerns for error handling:
- Base exceptions define the hierarchy
- CRUD exceptions handle database operations
- Auth exceptions handle authentication/authorization
- HTTP mapping is handled separately in app/core/error_handlers.py
"""

from app.exceptions.base import AppException
from app.exceptions.crud import (
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
)
from app.exceptions.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    InsufficientPermissionsError,
)

__all__ = [
    # Base
    "AppException",
    # CRUD
    "NotFoundError",
    "AlreadyExistsError",
    "ValidationError",
    # Auth
    "AuthenticationError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InsufficientPermissionsError",
]
