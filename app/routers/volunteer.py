"""Volunteer router module for CRUD endpoints."""

from datetime import date
from typing import Annotated, Literal
from anyio import to_thread

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user, get_current_volunteer
from app.models.user import User, UserCreate
from app.models.mission import MissionPublic
from app.models.volunteer import (
    Volunteer,
    VolunteerCreate,
    VolunteerPublic,
    VolunteerUpdate,
)
from app.services import volunteer as volunteer_service
from app.exceptions import NotFoundError, InsufficientPermissionsError
from app.utils.validation import ensure_id

router = APIRouter(prefix="/volunteers", tags=["volunteers"])


@router.post("/", response_model=VolunteerPublic)
def create_volunteer(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_in: UserCreate,
    volunteer_in: VolunteerCreate,
) -> VolunteerPublic:
    """
    Register a new volunteer with user account.

    Creates both a User account (with user_type=VOLUNTEER) and the associated
    Volunteer profile in a single atomic operation.

    ### What Gets Created:
    - User account with authentication credentials
    - Volunteer profile with personal information
    - Automatic linking between user and volunteer records

    Args:
        `user_in`: User account data including username, email, and password.
        `volunteer_in`: Volunteer profile data including name, phone number, birthdate,
            address (optional), and skills.
        `session`: Database session (automatically injected).

    Returns:
        `VolunteerPublic`: The newly created volunteer profile with user information,
            including id_volunteer and id_user.

    Raises:
        `400 AlreadyExistsError`: If the username or email already exists in the system.
    """
    volunteer = volunteer_service.create_volunteer(session, user_in, volunteer_in)
    session.commit()
    session.refresh(volunteer)
    return volunteer_service.to_volunteer_public(session, volunteer)


@router.get("/", response_model=list[VolunteerPublic])
def read_volunteers(
    session: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[VolunteerPublic]:
    """
    Retrieve a paginated list of all volunteers.

    Returns a list of all registered volunteers with their public profile information.
    Pagination parameters control the number of results returned.

    ### Pagination:
    - Default: Returns first 100 volunteers
    - Maximum limit: 100 volunteers per request
    - Use offset to skip records for subsequent pages

    Args:
        `offset`: Number of records to skip (default: 0, minimum: 0).
        `limit`: Maximum number of records to return (default: 100, range: 1-100).
        `session`: Database session (automatically injected).

    Returns:
        `list[VolunteerPublic]`: List of volunteer profiles with their public information,
            including mission counts and user details.
    """
    return volunteer_service.get_volunteers(session, offset=offset, limit=limit)


@router.get("/me", response_model=VolunteerPublic)
def read_current_volunteer(
    volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
    session: Annotated[Session, Depends(get_session)],
) -> VolunteerPublic:
    """
    Retrieve the authenticated user's volunteer profile.

    Returns the authenticated user's volunteer profile with all public information
    including active and finished mission counts.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `session`: Database session (automatically injected).
        `volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `VolunteerPublic`: The authenticated user's volunteer profile including personal
            information, mission statistics, and linked user account details.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If no volunteer profile exists for the authenticated user.
    """
    return volunteer_service.to_volunteer_public(session, volunteer)


@router.get("/me/missions", response_model=list[MissionPublic])
def read_current_volunteer_missions(
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
    target_date: Annotated[
        Literal["today"] | date | None,
        Query(
            description='Filter missions by date. Use "today" for current date, YYYY-MM-DD format for specific date, or omit to get all missions.',
            examples=["2026-01-15"],
        ),
    ] = None,
) -> list[MissionPublic]:
    """
    Retrieve the authenticated volunteer's missions with optional date filtering.

    Returns all missions where the authenticated user is an approved and active volunteer,
    optionally filtered to missions occurring on a specific date.

    ### Date Filtering Options:
    - **No parameter** (default): Returns all missions (past, present, and future)
    - **"today"**: Returns only missions active today
    - **Specific date** (YYYY-MM-DD): Returns missions active on that date

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `target_date`: Optional date filter. Use "today" for current date, YYYY-MM-DD format
            for a specific date, or omit entirely to get all missions.
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `list[MissionPublic]`: List of missions matching the filter criteria. Only includes
            missions where the volunteer's application has been approved and the volunteer is active.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user has no associated volunteer profile.
    """
    # Handle "today" string or actual date
    filter_date: date | None = None
    if target_date == "today":
        filter_date = date.today()
    elif target_date is not None:
        filter_date = target_date

    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")

    return volunteer_service.get_volunteer_missions(
        session, volunteer_id, target_date=filter_date
    )


@router.get("/{volunteer_id}", response_model=VolunteerPublic)
def read_volunteer(
    volunteer_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> VolunteerPublic:
    """
    Retrieve detailed volunteer profile information by ID.

    Retrieves complete public profile information for a specific volunteer,
    including their personal details, mission statistics, and user account information.

    Args:
        `volunteer_id`: The unique identifier of the volunteer to retrieve.
        `session`: Database session (automatically injected).

    Returns:
        `VolunteerPublic`: The volunteer's complete public profile including:
            - Personal information (name, phone, birthdate, etc.)
            - Mission statistics (active and finished counts)
            - Linked user account details

    Raises:
        `404 NotFoundError`: If no volunteer exists with the given ID.
    """
    volunteer = volunteer_service.get_volunteer(session, volunteer_id)
    if not volunteer:
        raise NotFoundError("Volunteer", volunteer_id)
    return volunteer_service.to_volunteer_public(session, volunteer)


@router.patch("/{volunteer_id}", response_model=VolunteerPublic)
def update_volunteer(
    volunteer_id: int,
    volunteer_update: VolunteerUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VolunteerPublic:
    """
    Update the authenticated user's volunteer profile information.

    Allows partial updates to volunteer profile fields. Only the fields included
    in the request body will be updated; omitted fields remain unchanged.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Only the profile owner can perform updates

    ### Updatable Fields:
    - Personal info: first_name, last_name, phone_number, birthdate
    - Location: address, zip_code
    - Additional: skills, bio
    - Account: email, password

    Args:
        `volunteer_id`: The unique identifier of the volunteer profile to update.
        `volunteer_update`: Object containing the fields to update. Only provided
            fields will be changed; others remain unchanged.
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `VolunteerPublic`: The updated volunteer profile with all current information.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `403 InsufficientPermissionsError`: If the authenticated user is not the profile owner.
        `404 NotFoundError`: If no volunteer exists with the given ID.
    """
    # Check volunteer exists and user owns it
    volunteer = volunteer_service.get_volunteer(session, volunteer_id)
    if not volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    if volunteer.id_user != current_user.id_user:
        raise InsufficientPermissionsError("update this volunteer profile")

    updated = volunteer_service.update_volunteer(
        session, volunteer_id, volunteer_update
    )
    session.commit()
    session.refresh(updated)
    return volunteer_service.to_volunteer_public(session, updated)


@router.delete("/{volunteer_id}", status_code=204)
async def delete_volunteer(
    volunteer_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete the volunteer profile and associated user account permanently.

    **⚠️ Warning**: This action is irreversible and will permanently delete:
    - The volunteer profile
    - The associated user account
    - All mission applications and engagements
    - The favorites list

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Only the profile owner can perform deletion

    Args:
        `volunteer_id`: The unique identifier of the volunteer profile to delete.
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `403 InsufficientPermissionsError`: If the authenticated user is not the profile owner.
        `404 NotFoundError`: If no volunteer exists with the given ID.
    """
    # Check volunteer exists and user owns it
    volunteer = volunteer_service.get_volunteer(session, volunteer_id)
    if not volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    if volunteer.id_user != current_user.id_user:
        raise InsufficientPermissionsError("delete this volunteer profile")

    await volunteer_service.delete_volunteer(session, volunteer_id)
    await to_thread.run_sync(session.commit)


# Favorite endpoints


@router.get("/me/favorites", response_model=list[MissionPublic])
def read_favorite_missions(
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
) -> list[MissionPublic]:
    """
    Retrieve the authenticated volunteer's favorite missions list.

    Retrieves all missions marked as favorites by the authenticated user. Favorites allow
    users to save missions of interest for quick access later.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `list[MissionPublic]`: The authenticated user's favorite missions, ordered by most
            recently added first. Each mission includes full details like location, dates, and description.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user has no volunteer profile.
    """
    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")
    return volunteer_service.get_favorite_missions(session, volunteer_id)


@router.post("/me/favorites/{mission_id}", status_code=201)
def add_favorite_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
) -> None:
    """
    Add a mission to the authenticated volunteer's favorites list.

    Mark a mission as a favorite to save it for quick access later. Users can
    favorite any mission regardless of application status.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `mission_id`: The unique identifier of the mission to add to favorites.
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `None`: Returns 201 Created on success.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the user has no volunteer profile or the mission doesn't exist.
        `400 AlreadyExistsError`: If the mission is already in the user's favorites list.
    """
    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")
    volunteer_service.add_favorite_mission(session, volunteer_id, mission_id)
    session.commit()


@router.delete("/me/favorites/{mission_id}", status_code=204)
def remove_favorite_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
) -> None:
    """
    Remove a mission from the authenticated volunteer's favorites list.

    Unfavorite a mission to remove it from saved favorites. This does not
    affect application or participation status for the mission.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `mission_id`: The unique identifier of the mission to remove from favorites.
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `None`: Returns 204 No Content on successful removal.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the volunteer profile doesn't exist or the mission
            is not in the favorites list.
    """
    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")
    volunteer_service.remove_favorite_mission(session, volunteer_id, mission_id)
    session.commit()


# Application/Engagement endpoints


@router.post("/me/missions/{mission_id}/apply", status_code=201)
def apply_to_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
    message: str | None = None,
) -> None:
    """
    Submit a mission application for the authenticated volunteer.

    Submit an application to participate in a mission. The application will be
    reviewed by the mission's association.

    ### Application Process:
    1. **Submit**: Application submitted with optional message
    2. **Pending**: Application status is PENDING awaiting association review
    3. **Decision**: Association either approves or rejects the application
    4. **Active**: If approved, volunteer becomes active for the mission

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `mission_id`: The unique identifier of the mission to apply for.
        `message`: Optional message to the association explaining the motivation to volunteer
            (maximum 1000 characters).
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `None`: Returns 201 Created on successful application submission.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the volunteer profile or the mission doesn't exist.
        `400 AlreadyExistsError`: If an application for this mission already exists.
    """
    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")
    volunteer_service.apply_to_mission(session, volunteer_id, mission_id, message)
    session.commit()


@router.delete("/me/missions/{mission_id}/application", status_code=204)
async def withdraw_application(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_volunteer: Annotated[Volunteer, Depends(get_current_volunteer)],
) -> None:
    """
    Withdraw a pending mission application for the authenticated volunteer.

    Cancel an application that is still awaiting review. Only applications
    in PENDING status can be withdrawn. Sends notification to association.

    ### Important Notes:
    - **Only PENDING applications** can be withdrawn
    - **Approved applications** cannot be withdrawn (contact the association instead)
    - **Rejected applications** cannot be withdrawn (already processed)
    - After withdrawal, reapplication is possible

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `mission_id`: The unique identifier of the mission whose application to withdraw.
        `session`: Database session (automatically injected).
        `current_volunteer`: Authenticated volunteer profile (automatically injected).

    Returns:
        `None`: Returns 204 No Content on successful withdrawal.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the volunteer profile doesn't exist or no pending
            application exists for this mission.
    """
    volunteer_id = ensure_id(current_volunteer.id_volunteer, "Volunteer")
    await to_thread.run_sync(
        volunteer_service.withdraw_application, session, volunteer_id, mission_id
    )
    await to_thread.run_sync(session.commit)
