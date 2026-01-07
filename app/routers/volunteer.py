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
        offset (int): Number of records to skip.
        limit (int): Maximum number of records to return (1–100).

    Returns:
        list[VolunteerPublic]: Public representations of volunteers.
    """
    return volunteer_service.get_volunteers(session, offset=offset, limit=limit)


@router.get("/me", response_model=VolunteerPublic)
def read_current_volunteer(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VolunteerPublic:
    """
    Return the authenticated user's volunteer profile.

    Returns:
        VolunteerPublic: The public representation of the volunteer associated with the authenticated user.

    Raises:
        NotFoundError: If no volunteer profile exists for the authenticated user.
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
        Literal["today"] | date | None,
        Query(
            description="Filter by date (YYYY-MM-DD or 'today'). Omit for all missions."
        ),
    ] = None,
) -> list[MissionPublic]:
    """
    Get the current authenticated volunteer's missions, optionally filtered to a specific date.

    If `target_date` is "today" the filter uses the current date; if a `date` is provided it filters to that date; if omitted it returns missions for all dates.

    Parameters:
        target_date (Literal["today"] | date | None): Filter by date (YYYY-MM-DD) or the string "today"; omit to return all missions.

    Returns:
        list[MissionPublic]: Missions for which the volunteer is approved and active on the specified date (or all missions if no date provided).

    Raises:
        NotFoundError: If the current user has no associated volunteer profile.
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
    Retrieve a volunteer by its ID.

    Returns:
        VolunteerPublic: The volunteer's public representation, including linked user information.

    Raises:
        NotFoundError: If no volunteer exists with the given ID.
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

    Only the volunteer who owns the profile may perform this update.

    Parameters:
        volunteer_id (int): Primary key of the volunteer to update.
        volunteer_update (VolunteerUpdate): Fields to update; only provided fields will be changed.

    Returns:
        VolunteerPublic: The updated volunteer in its public representation.

    Raises:
        NotFoundError: If no volunteer exists with the given ID.
        InsufficientPermissionsError: If the current user is not the owner of the volunteer profile.
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
    Retrieve the current authenticated volunteer's favorite missions.

    Returns:
        list[MissionPublic]: Favorite missions for the current volunteer, ordered by most recent first.

    Raises:
        NotFoundError: If the current user has no volunteer profile.
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
    Add a mission to the authenticated volunteer's favorites.

    Raises:
        NotFoundError: If the authenticated user has no volunteer profile or the mission does not exist.
        AlreadyExistsError: If the mission is already in the volunteer's favorites.
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
    Remove a mission from the authenticated volunteer's favorites.

    Parameters:
        mission_id (int): ID of the mission to remove from the volunteer's favorites.

    Raises:
        NotFoundError: If the volunteer profile does not exist or the favorite association is not found.
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


# Application/Engagement endpoints


@router.post("/me/missions/{mission_id}/apply", status_code=201)
def apply_to_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    message: str | None = None,
) -> None:
    """
    Apply to a mission as the authenticated volunteer.

    Creates a PENDING engagement that requires association approval.

    Parameters:
        mission_id: The mission's primary key.
        message: Optional application message to the association.

    Raises:
        NotFoundError: If the volunteer profile or mission doesn't exist.
        AlreadyExistsError: If the volunteer already has an application for this mission.
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None
    volunteer_service.apply_to_mission(
        session, volunteer.id_volunteer, mission_id, message
    )


@router.delete("/me/missions/{mission_id}/application", status_code=204)
def withdraw_application(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Withdraw a PENDING application for a mission.

    Only pending applications can be withdrawn. Approved or rejected applications
    cannot be withdrawn.

    Parameters:
        mission_id: The mission's primary key.

    Raises:
        NotFoundError: If the volunteer profile doesn't exist or no pending application exists.
    """
    assert current_user.id_user is not None
    volunteer = volunteer_service.get_volunteer_by_user_id(
        session, current_user.id_user
    )
    if not volunteer:
        raise NotFoundError("Volunteer profile", current_user.id_user)

    assert volunteer.id_volunteer is not None
    volunteer_service.withdraw_application(session, volunteer.id_volunteer, mission_id)
