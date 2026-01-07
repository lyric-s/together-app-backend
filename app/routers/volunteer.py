"""Volunteer router module for CRUD endpoints."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User, UserCreate
from app.models.mission import MissionPublic
from app.models.volunteer import (
    VolunteerCreate,
    VolunteerPublic,
    VolunteerUpdate,
)
from app.services import volunteer as volunteer_service
from app.exceptions import NotFoundError, InsufficientPermissionsError

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

    Creates both a User (with user_type=VOLUNTEER) and the associated Volunteer
    profile in a single operation.

    Parameters:
        user_in: User account data (username, email, password).
        volunteer_in: Volunteer profile data (name, phone, birthdate, etc.).

    Returns:
        VolunteerPublic: The created volunteer with user information.

    Raises:
        AlreadyExistsError: If username or email already exists (400).
    """
    volunteer = volunteer_service.create_volunteer(session, user_in, volunteer_in)
    return volunteer_service.to_volunteer_public(session, volunteer)


@router.get("/", response_model=list[VolunteerPublic])
def read_volunteers(
    session: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[VolunteerPublic]:
    """
    Retrieve a paginated list of volunteers.

    Parameters:
        offset: Number of records to skip (default 0).
        limit: Maximum number of records to return (default 100, max 100).

    Returns:
        list[VolunteerPublic]: List of volunteer records with user information.
    """
    return volunteer_service.get_volunteers(session, offset=offset, limit=limit)


@router.get("/me", response_model=VolunteerPublic)
def read_current_volunteer(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VolunteerPublic:
    """
    Retrieve the current authenticated user's volunteer profile.

    Returns:
        VolunteerPublic: The volunteer profile of the authenticated user.

    Raises:
        NotFoundError: If the user has no volunteer profile (404).
    """
    # current_user.id_user is guaranteed to be int after authentication
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)
    return volunteer_service.to_volunteer_public(session, volunteer)


@router.get("/me/missions", response_model=list[MissionPublic])
def read_current_volunteer_missions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    target_date: Annotated[
        date | Literal["today"] | None,
        Query(
            description="Filter by date (YYYY-MM-DD or 'today'). Omit for all missions."
        ),
    ] = None,
) -> list[MissionPublic]:
    """
    Retrieve the current volunteer's missions, optionally filtered by date.

    Parameters:
        target_date: Optional filter - a specific date (YYYY-MM-DD), "today", or omit for all.

    Returns:
        list[MissionPublic]: Missions where the volunteer is approved and active on the date.

    Raises:
        NotFoundError: If the user has no volunteer profile (404).
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None

    # Handle "today" string or actual date
    filter_date: date | None = None
    if target_date == "today":
        filter_date = date.today()
    elif target_date is not None:
        filter_date = target_date

    return volunteer_service.get_volunteer_missions(
        session, volunteer.id_volunteer, target_date=filter_date
    )


@router.get("/{volunteer_id}", response_model=VolunteerPublic)
def read_volunteer(
    volunteer_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> VolunteerPublic:
    """
    Retrieve a specific volunteer by ID.

    Parameters:
        volunteer_id: The volunteer's primary key.

    Returns:
        VolunteerPublic: The volunteer record with user information.

    Raises:
        NotFoundError: If no volunteer exists with the given ID (404).
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
    Update a volunteer's profile information.

    Only the volunteer themselves can update their profile.

    Parameters:
        volunteer_id: The volunteer's primary key.
        volunteer_update: Partial update data; only provided fields will be applied.

    Returns:
        VolunteerPublic: The updated volunteer record.

    Raises:
        NotFoundError: If no volunteer exists with the given ID (404).
        InsufficientPermissionsError: If the user is not the volunteer owner (403).
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
    return volunteer_service.to_volunteer_public(session, updated)


@router.delete("/{volunteer_id}", status_code=204)
def delete_volunteer(
    volunteer_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a volunteer and their associated user account.

    Only the volunteer themselves can delete their account.

    Parameters:
        volunteer_id: The volunteer's primary key.

    Raises:
        NotFoundError: If no volunteer exists with the given ID (404).
        InsufficientPermissionsError: If the user is not the volunteer owner (403).
    """
    # Check volunteer exists and user owns it
    volunteer = volunteer_service.get_volunteer(session, volunteer_id)
    if not volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    if volunteer.id_user != current_user.id_user:
        raise InsufficientPermissionsError("delete this volunteer profile")

    volunteer_service.delete_volunteer(session, volunteer_id)


# Favorite endpoints


@router.get("/me/favorites", response_model=list[MissionPublic])
def read_favorite_missions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MissionPublic]:
    """
    Retrieve the current volunteer's favorite missions.

    Returns:
        list[MissionPublic]: List of favorited missions, ordered by most recent first.

    Raises:
        NotFoundError: If the user has no volunteer profile (404).
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None
    return volunteer_service.get_favorite_missions(session, volunteer.id_volunteer)


@router.post("/me/favorites/{mission_id}", status_code=201)
def add_favorite_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Add a mission to the current volunteer's favorites.

    Parameters:
        mission_id: The mission's primary key.

    Raises:
        NotFoundError: If the user has no volunteer profile or mission doesn't exist (404).
        AlreadyExistsError: If the mission is already favorited (400).
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None
    volunteer_service.add_favorite_mission(session, volunteer.id_volunteer, mission_id)


@router.delete("/me/favorites/{mission_id}", status_code=204)
def remove_favorite_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Remove a mission from the current volunteer's favorites.

    Parameters:
        mission_id: The mission's primary key.

    Raises:
        NotFoundError: If the user has no volunteer profile or favorite doesn't exist (404).
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None
    volunteer_service.remove_favorite_mission(
        session, volunteer.id_volunteer, mission_id
    )
