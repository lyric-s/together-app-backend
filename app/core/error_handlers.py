"""HTTP error handlers for FastAPI application.

This module provides the bridge between application exceptions and HTTP responses.
It maps domain-level exceptions to appropriate HTTP status codes and response formats.

Purpose:
    - Keep HTTP concerns separate from business logic
    - Provide consistent error response format across the API
    - Allow easy modification of HTTP responses without changing domain logic
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.exceptions import (
    AppException,
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
    AuthenticationError,
    InsufficientPermissionsError,
)


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Map NotFoundError to 404 Not Found response."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


async def already_exists_handler(
    request: Request, exc: AlreadyExistsError
) -> JSONResponse:
    """Map AlreadyExistsError to 400 Bad Request response."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Map ValidationError to 422 Unprocessable Entity response."""
    content = {"detail": str(exc)}
    if exc.field:
        content["field"] = exc.field
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content
    )


async def insufficient_permissions_handler(
    request: Request, exc: InsufficientPermissionsError
) -> JSONResponse:
    """Map InsufficientPermissionsError to 403 Forbidden response."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)}
    )


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """Map AuthenticationError to 401 Unauthorized response with WWW-Authenticate header."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},  # OAuth2 spec compliance
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Catch-all handler for unhandled application exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred"},
    )


def register_exception_handlers(app) -> None:
    """
    Register all HTTP error handlers with the FastAPI application.

    Handlers are registered in order from most specific to most general.
    This ensures that specific exceptions are caught before their parent classes.

    Args:
        app: FastAPI application instance
    """
    # CRUD exception handlers
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(AlreadyExistsError, already_exists_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)

    # Auth exception handlers (specific before general)
    app.add_exception_handler(
        InsufficientPermissionsError, insufficient_permissions_handler
    )
    app.add_exception_handler(AuthenticationError, authentication_error_handler)

    # Catch-all for unhandled application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
