"""Authentication and authorization exceptions."""

from app.exceptions.base import AppException


class AuthenticationError(AppException):
    """Base class for authentication-related errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Username/email or password is incorrect."""

    def __init__(self, message: str = "Incorrect username or password"):
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Token is invalid, expired, or malformed."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class TokenExpiredError(InvalidTokenError):
    """Token has expired (more specific than InvalidTokenError)."""

    def __init__(self, token_type: str = "access"):
        super().__init__(f"{token_type.capitalize()} token has expired")
        self.token_type = token_type


class InsufficientPermissionsError(AuthenticationError):
    """User doesn't have required permissions for this action."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message)
