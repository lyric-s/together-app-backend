"""Shared service layer utilities."""

from typing import TypeVar, Type
from sqlmodel import Session

from app.exceptions.crud import NotFoundError

T = TypeVar("T")


def get_or_404(
    session: Session,
    model_class: Type[T],
    entity_id: int,
    entity_name: str | None = None,
) -> T:
    """
    Retrieve an entity by ID or raise NotFoundError.

    More efficient than select().where() as it uses session.get() which
    checks the session identity map before querying the database.

    Parameters:
        session: Database session.
        model_class: SQLModel class to query.
        entity_id: Primary key value.
        entity_name: Optional custom name for error message (defaults to model class name).

    Returns:
        T: The retrieved entity instance.

    Raises:
        NotFoundError: If entity doesn't exist.

    Example:
        user = get_or_404(session, User, user_id, "User")
    """
    entity = session.get(model_class, entity_id)
    if not entity:
        name = entity_name or model_class.__name__
        raise NotFoundError(name, entity_id)
    return entity
