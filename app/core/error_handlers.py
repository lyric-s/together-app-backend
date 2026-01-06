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
    """
    Map a NotFoundError to an HTTP 404 JSON response.

    Returns:
        JSONResponse: Response with status 404 and a JSON body `{"detail": "<exception message>"}`.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


async def already_exists_handler(
    request: Request, exc: AlreadyExistsError
) -> JSONResponse:
    """
    Convert an AlreadyExistsError into an HTTP 400 Bad Request JSON response.

    Returns:
        JSONResponse: Response with status code 400 and content containing a `detail` key with the exception message.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)}
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Convert a ValidationError into an HTTP 422 Unprocessable Entity JSON response.

    Parameters:
        exc (ValidationError): The domain validation error; if `exc.field` is set, the response will include a `field` key indicating the related field.

    Returns:
        JSONResponse: Response with status 422 and a JSON body containing a `detail` message and, when available, a `field` key.
    """
    content = {"detail": str(exc)}
    if exc.field:
        content["field"] = exc.field
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content
    )


async def insufficient_permissions_handler(
    request: Request, exc: InsufficientPermissionsError
) -> JSONResponse:
    """
    Handle an InsufficientPermissionsError by returning a 403 Forbidden JSON response.

    @returns JSONResponse with status code 403 and a `detail` field containing the exception message.
    """
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)}
    )


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """
    Convert an AuthenticationError into a 401 Unauthorized JSON response that includes a WWW-Authenticate header.

    Parameters:
        request (Request): The incoming HTTP request that triggered the exception.
        exc (AuthenticationError): The authentication failure to expose in the response.

    Returns:
        JSONResponse: Response with status 401, a JSON body containing a `detail` string from `exc`, and `WWW-Authenticate: Bearer` header.
    """
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},  # OAuth2 spec compliance
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle unhandled application-level exceptions and produce a standardized 500 Internal Server Error response.

    Returns:
        JSONResponse: HTTP 500 response with content {"detail": "An internal error occurred"}.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred"},
    )


def register_exception_handlers(app) -> None:
    """
    Register the application's domain-to-HTTP exception handlers on a FastAPI app.

    Registers handlers in order from most specific to most general so that subclassed
    exceptions are matched before their parent types. The following mappings are added:
    NotFoundError -> 404, AlreadyExistsError -> 400, ValidationError -> 422
    (includes optional `field`), InsufficientPermissionsError -> 403,
    AuthenticationError -> 401 (adds `WWW-Authenticate: Bearer`), and AppException -> 500.

    Parameters:
        app: The FastAPI application instance to which the exception handlers will be attached.
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
