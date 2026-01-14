"""Public category router for browsing mission categories."""

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database.database import get_session
from app.models.category import CategoryPublic
from app.services import category as category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryPublic])
def get_all_categories(
    session: Annotated[Session, Depends(get_session)],
) -> list[CategoryPublic]:
    """
    Retrieve all mission categories.

    Public endpoint - no authentication required. Used by frontend to populate
    category filter dropdowns and display category information.

    Categories are returned alphabetically by label for consistent display.

    Returns:
        `list[CategoryPublic]`: All available categories sorted alphabetically.

    Example response:
        [
            {"id_categ": 1, "label": "Accompagnement seniors"},
            {"id_categ": 2, "label": "Aide administrative"},
            {"id_categ": 3, "label": "Aide alimentaire"},
            ...
        ]
    """
    categories = category_service.get_all_categories(session)
    return [CategoryPublic.model_validate(c) for c in categories]
