"""CRUD-related exceptions for database operations."""

from app.exceptions.base import AppException


class NotFoundError(AppException):
    """Resource not found in the database."""

    def __init__(self, resource: str, identifier: int | str):
        """
        Initialize a NotFoundError for a missing resource.

        Parameters:
            resource (str): The type or name of the resource that was not found.
            identifier (int | str): The identifier of the missing resource.

        Description:
            Stores `resource` and `identifier` as instance attributes and sets the exception message to
            "<resource> with identifier '<identifier>' not found".
        """
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with identifier '{identifier}' not found")


class AlreadyExistsError(AppException):
    """Resource already exists (unique constraint violation)."""

    def __init__(self, resource: str, field: str, value: int | str):
        """
        Indicates a unique-constraint violation for a resource when a specific field value already exists.

        Parameters:
            resource (str): Name of the resource type (for example, "User").
            field (str): The field that must be unique (for example, "email").
            value (int | str): The conflicting value for the field.
        """
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field}='{value}' already exists")


class ValidationError(AppException):
    """Business logic validation failed."""

    def __init__(self, message: str, field: str | None = None):
        """
        Create a ValidationError representing a business logic validation failure.

        Parameters:
            message (str): Human-readable error message describing the validation failure.
            field (str | None): Optional name of the field associated with the validation error; may be None if not field-specific.
        """
        self.field = field
        super().__init__(message)
