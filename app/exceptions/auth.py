"""Authentication and authorization exceptions."""

from app.exceptions.base import AppException


class AuthenticationError(AppException):
    """Base class for authentication-related errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Username/email or password is incorrect."""

    def __init__(self, message: str = "Incorrect username or password"):
        """
        Initialize the InvalidCredentialsError with a human-readable message.

        Parameters:
            message: Custom error message describing the authentication failure; defaults to "Incorrect username or password".
        """
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Token is invalid, expired, or malformed."""

    def __init__(self, message: str = "Invalid or expired token"):
        """
        Initialize the InvalidTokenError with a descriptive message.

        Parameters:
            message (str): Error message describing the token problem. Defaults to "Invalid or expired token".
        """
        super().__init__(message)


class TokenExpiredError(InvalidTokenError):
    """Token has expired (more specific than InvalidTokenError)."""

    def __init__(self, token_type: str = "access"):
        """
        Initialize a TokenExpiredError for a specific token type.

        Parameters:
            token_type (str): Type of the expired token (e.g., "access" or "refresh"). This value is stored on the instance as `token_type` and is capitalized and included in the exception message as "<TokenType> token has expired".
        """
        super().__init__(f"{token_type.capitalize()} token has expired")
        self.token_type = token_type


class InsufficientPermissionsError(AuthenticationError):
    """User doesn't have required permissions for this action."""

    def __init__(self, message: str = "Insufficient permissions"):
        """
        Initialize InsufficientPermissionsError with an optional message describing the permission failure.

        Parameters:
            message (str): Human-readable error message; defaults to "Insufficient permissions".
        """
        super().__init__(message)
