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
    This endpoint supports advanced filtering and full-text search to help volunteers
    find relevant opportunities.

    ## Query Parameters

    All parameters are optional and can be combined:

    - `category_ids` (string): Comma-separated category IDs with OR logic (e.g., "1,3,5")
    - `country` (string): Filter by exact country name match (e.g., "France")
    - `zip_code` (string): Filter by zip code prefix (e.g., "75" matches all Paris codes)
    - `date_available` (date): Show missions active on/after this date (ISO 8601 format)
    - `search` (string): Case-insensitive text search in mission name and description
    - `show_full` (boolean): Include missions at capacity (default: `true`)
    - `offset` (integer): Pagination offset, starts at 0 (default: `0`)
    - `limit` (integer): Results per page, max 100 (default: `100`)
    - `sort_by` (string): Sort field - `date_start`, `name`, or `created_at` (default: `date_start`)

    ## Example Requests

    **Basic search - all missions:**
    ```
    GET /missions
    ```

    **Category filtering (OR logic):**
    ```
    GET /missions?category_ids=1,5&limit=10
    ```

    **Location and date filtering:**
    ```
    GET /missions?country=France&zip_code=75&date_available=2026-02-01
    ```

    **Text search for available missions:**
    ```
    GET /missions?search=food%20bank&show_full=false&sort_by=name
    ```

    ## Example Response

    ```json
    [
      {
        "id_mission": 42,
        "name": "Community Food Bank Volunteer",
        "description": "Help sort and distribute food to families in need",
        "date_start": "2026-02-15",
        "date_end": "2026-02-15",
        "duration_hours": 4.0,
        "skills_required": "Organization, Physical stamina",
        "max_volunteers": 10,
        "enrolled_count": 7,
        "available_slots": 3,
        "is_full": false,
        "location": {
          "address": "123 Main St",
          "country": "France",
          "zip_code": "75001"
        },
        "categories": [
          {"id_categ": 1, "name": "Social Services"}
        ],
        "association": {
          "id_asso": 5,
          "name": "Paris Food Bank",
          "rna": "W751234567"
        }
      }
    ]
    ```

    ## Response Details

    Each mission includes:
    - **Mission info**: Name, description, dates, required skills
    - **Capacity tracking**: Max volunteers, enrolled count, available slots, `is_full` status
    - **Location**: Full address with country and zip code
    - **Categories**: All assigned categories (multi-category support)
    - **Association**: Public profile of the organizing non-profit

    Parameters:
        session: Database session (automatically injected via `Depends(get_session)`).
        category_ids: Comma-separated category IDs for filtering (OR logic).
        country: Filter by exact country name.
        zip_code: Filter by zip code prefix.
        date_available: Show missions active on/after this date.
        search: Text search in name and description.
        show_full: Include full missions (default: `true`).
        offset: Pagination offset (default: `0`).
        limit: Results per page, max 100 (default: `100`).
        sort_by: Sort field (default: `date_start`).

    Returns:
        `list[MissionPublic]`: List of missions matching the search criteria.

    Raises:
        `422 ValidationError`: If query parameters fail validation (invalid category_ids format, etc.).
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
    Use this endpoint to display a mission detail page with all information
    volunteers need to make an informed decision.

    ## Example Request

    ```
    GET /missions/42
    ```

    ## Example Response

    ```json
    {
      "id_mission": 42,
      "name": "Community Food Bank Volunteer",
      "description": "Help sort and distribute food to families in need. Tasks include organizing donations, packing boxes, and helping with distribution.",
      "date_start": "2026-02-15",
      "date_end": "2026-02-15",
      "duration_hours": 4.0,
      "skills_required": "Organization, Physical stamina, Teamwork",
      "max_volunteers": 10,
      "enrolled_count": 7,
      "available_slots": 3,
      "is_full": false,
      "location": {
        "id_location": 8,
        "address": "123 Main Street",
        "zip_code": "75001",
        "city": "Paris",
        "country": "France",
        "latitude": 48.8566,
        "longitude": 2.3522
      },
      "categories": [
        {"id_categ": 1, "name": "Social Services"},
        {"id_categ": 5, "name": "Community"}
      ],
      "association": {
        "id_asso": 5,
        "name": "Paris Food Bank",
        "rna": "W751234567",
        "description": "Fighting food insecurity in Paris since 1995"
      }
    }
    ```

    ## Response Details

    Returns complete mission information including:
    - **Mission details**: Name, dates, description, skills required, duration
    - **Capacity tracking**: Max volunteers, enrolled count, available slots, `is_full` status
    - **Location**: Full address with coordinates for mapping
    - **Categories**: All assigned categories (multi-category support)
    - **Association profile**: Public information about the organizing non-profit

    Parameters:
        mission_id: The unique identifier of the mission to retrieve.
        session: Database session (automatically injected via `Depends(get_session)`).

    Returns:
        `MissionPublic`: Complete mission details with capacity tracking and related entities.

    Raises:
        `404 NotFoundError`: If mission with the specified ID doesn't exist.
    """
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    return mission_service.to_mission_public(session, mission)
