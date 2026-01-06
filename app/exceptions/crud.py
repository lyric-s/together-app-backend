"""CRUD-related exceptions for database operations."""

from app.exceptions.base import AppException


class NotFoundError(AppException):
    """Resource not found in the database."""

    def __init__(self, resource: str, identifier: int | str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with identifier '{identifier}' not found")


class AlreadyExistsError(AppException):
    """Resource already exists (unique constraint violation)."""

    def __init__(self, resource: str, field: str, value: str):
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field}='{value}' already exists")


class ValidationError(AppException):
    """Business logic validation failed."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message)
