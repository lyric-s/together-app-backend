"""Public mission discovery router."""

from typing import Annotated
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database.database import get_session
from app.models.mission import MissionPublic
from app.services import mission as mission_service
from app.exceptions import NotFoundError

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/", response_model=list[MissionPublic])
def search_missions(
    session: Annotated[Session, Depends(get_session)],
    category_ids: Annotated[
        str | None,
        Query(
            description="Comma-separated category IDs (OR logic - missions matching ANY category)",
            examples=["1,3,5"],
        ),
    ] = None,
    country: str | None = Query(default=None, description="Filter by location country"),
    zip_code: str | None = Query(default=None, description="Filter by zip code prefix"),
    date_available: date | None = Query(
        default=None,
        description="Show missions active on/after this date (defaults to today)",
    ),
    search: str | None = Query(
        default=None, description="Text search in mission name and description"
    ),
    show_full: bool = Query(
        default=True,
        description="Include full missions (when false, hides missions at capacity)",
    ),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(
        default=100, ge=1, le=100, description="Pagination limit (max 100)"
    ),
    sort_by: str = Query(
        default="date_start",
        pattern="^(date_start|name|created_at)$",
        description="Sort field: date_start, name, or created_at",
    ),
) -> list[MissionPublic]:
    """
    Public endpoint to discover and search missions.

    No authentication required - allows public browsing of available missions.

    ### Filters:
    - **category_ids**: Missions matching ANY of the provided categories (OR logic)
    - **country**: Filter by exact location country match
    - **zip_code**: Filter by zip code prefix (e.g., "75" matches "75001", "75002", etc.)
    - **date_available**: Show missions active on/after this date (defaults to today)
    - **search**: Case-insensitive text search in mission name and description
    - **show_full**: Include missions at full capacity (default: true)

    ### Response includes:
    - Location details (address, country, zip_code, coordinates)
    - All assigned categories (multi-category support)
    - Association info (public profile)
    - Capacity tracking (enrolled volunteers, available slots, is_full status)

    ### Example queries:
    - `/missions` - All future missions
    - `/missions?category_ids=1,5` - Missions in categories 1 OR 5
    - `/missions?country=France&zip_code=75` - Missions in Paris
    - `/missions?search=food&show_full=false` - Available food-related missions
    """
    # Parse category_ids from comma-separated string
    parsed_category_ids = None
    if category_ids:
        parsed_category_ids = [int(id.strip()) for id in category_ids.split(",")]

    missions = mission_service.search_missions(
        session,
        category_ids=parsed_category_ids,
        country=country,
        zip_code=zip_code,
        date_available=date_available,
        search=search,
        show_full=show_full,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
    )

    # Convert to MissionPublic with capacity info
    return [mission_service.to_mission_public(session, m) for m in missions]


@router.get("/{mission_id}", response_model=MissionPublic)
def get_mission_details(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> MissionPublic:
    """
    Get detailed information about a specific mission.

    No authentication required - public endpoint for viewing mission details.

    Returns complete mission information including:
    - Mission details (name, dates, description, skills, capacity)
    - Location (address, country, zip code, coordinates)
    - Categories (all assigned categories)
    - Association profile (public information)
    - Capacity tracking (enrolled count, available slots, is_full status)

    Args:
        mission_id: The unique identifier of the mission.
        session: Database session (automatically injected).

    Returns:
        MissionPublic: Complete mission details with capacity tracking.

    Raises:
        404 NotFoundError: If mission doesn't exist.
    """
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    return mission_service.to_mission_public(session, mission)
