"""Volunteer service module for CRUD operations."""

from datetime import date

from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.models.volunteer import (
    Volunteer,
    VolunteerCreate,
    VolunteerUpdate,
    VolunteerPublic,
)
from app.models.user import UserCreate, UserUpdate, UserPublic
from app.models.engagement import Engagement
from app.models.favorite import Favorite
from app.models.mission import Mission, MissionPublic
from app.models.enums import UserType, ProcessingStatus
from app.exceptions import NotFoundError, AlreadyExistsError
from app.services import user as user_service


def _compute_mission_counts(session: Session, volunteer_id: int) -> tuple[int, int]:
    """
    Compute the number of active and finished missions for a volunteer.

    Active missions are approved engagements whose mission end date is today or later.
    Finished missions are approved engagements whose mission end date is before today.

    Returns:
        tuple[int, int]: (active_missions_count, finished_missions_count)
    """
    today = date.today()

    # Count active missions (approved engagements with ongoing missions)
    active_stmt = (
        select(func.count())
        .select_from(Engagement)
        .join(Mission, Engagement.id_mission == Mission.id_mission)  # type: ignore
        .where(
            Engagement.id_volunteer == volunteer_id,
            Engagement.state == ProcessingStatus.APPROVED,
            Mission.date_end >= today,
        )
    )
    active_count = session.exec(active_stmt).one()

    # Count finished missions (approved engagements with past missions)
    finished_stmt = (
        select(func.count())
        .select_from(Engagement)
        .join(Mission, Engagement.id_mission == Mission.id_mission)  # type: ignore
        .where(
            Engagement.id_volunteer == volunteer_id,
            Engagement.state == ProcessingStatus.APPROVED,
            Mission.date_end < today,
        )
    )
    finished_count = session.exec(finished_stmt).one()

    return active_count, finished_count


def _compute_mission_counts_batch(
    session: Session, volunteer_ids: list[int]
) -> dict[int, tuple[int, int]]:
    """
    Compute active and finished mission counts for the given volunteers.

    Counts are taken from engagements with state APPROVED. For each engagement, if the mission's end date is today or later it is considered active; if it is before today it is considered finished.

    Returns:
        dict[int, tuple[int, int]]: Mapping from volunteer_id to a tuple (active_count, finished_count).
    """
    if not volunteer_ids:
        return {}

    today = date.today()

    # Base query for approved engagements
    base_query = (
        select(Engagement.id_volunteer, Mission.date_end)  # type: ignore
        .join(Mission, Engagement.id_mission == Mission.id_mission)  # type: ignore
        .where(
            Engagement.id_volunteer.in_(volunteer_ids),  # type: ignore
            Engagement.state == ProcessingStatus.APPROVED,
        )
    )

    results = session.exec(base_query).all()

    # Aggregate in Python to avoid complex group by logic
    counts: dict[int, list[int]] = {vid: [0, 0] for vid in volunteer_ids}

    for vid, end_date in results:
        if end_date >= today:
            counts[vid][0] += 1  # Active
        else:
            counts[vid][1] += 1  # Finished

    return {k: (v[0], v[1]) for k, v in counts.items()}


def to_volunteer_public(session: Session, volunteer: Volunteer) -> VolunteerPublic:
    """
    Create a public-facing Volunteer representation with computed mission counts and optional public user data.

    Parameters:
        volunteer (Volunteer): Volunteer model with a populated `id_volunteer` (required).

    Returns:
        VolunteerPublic: Public representation of the volunteer containing the volunteer's fields (excluding `user`, `badges`, and `missions`), `active_missions_count`, `finished_missions_count`, and `user` set to a `UserPublic` when an associated user exists.
    """
    assert volunteer.id_volunteer is not None
    active_count, finished_count = _compute_mission_counts(
        session, volunteer.id_volunteer
    )

    user_public = None
    if volunteer.user:
        user_public = UserPublic.model_validate(volunteer.user)

    return VolunteerPublic(
        **volunteer.model_dump(exclude={"user", "badges", "missions"}),
        active_missions_count=active_count,
        finished_missions_count=finished_count,
        user=user_public,
    )


def to_volunteer_public_from_batch(
    volunteers: list[Volunteer], counts_map: dict[int, tuple[int, int]]
) -> list[VolunteerPublic]:
    """
    Convert Volunteer models into their public representation using precomputed mission counts.

    Parameters:
        volunteers (list[Volunteer]): Volunteer database models to convert.
        counts_map (dict[int, tuple[int, int]]): Mapping from volunteer ID to a tuple
            (active_missions_count, finished_missions_count). If an ID is missing,
            counts default to (0, 0).

    Returns:
        list[VolunteerPublic]: Public-facing volunteer models with embedded `user`
        when present and mission counts populated.
    """
    results = []
    for volunteer in volunteers:
        assert volunteer.id_volunteer is not None
        active_count, finished_count = counts_map.get(volunteer.id_volunteer, (0, 0))

        user_public = None
        if volunteer.user:
            user_public = UserPublic.model_validate(volunteer.user)

        results.append(
            VolunteerPublic(
                **volunteer.model_dump(exclude={"user", "badges", "missions"}),
                active_missions_count=active_count,
                finished_missions_count=finished_count,
                user=user_public,
            )
        )
    return results


def create_volunteer(
    session: Session, user_in: UserCreate, volunteer_in: VolunteerCreate
) -> Volunteer:
    """
    Create a Volunteer and its associated User account.

    Sets the provided user's user_type to VOLUNTEER, creates the User, then creates
    and persists a Volunteer profile linked to that User.

    Parameters:
        user_in (UserCreate): User creation data (username, email, password).
        volunteer_in (VolunteerCreate): Volunteer profile data (name, phone, birthdate, etc.).

    Returns:
        Volunteer: The created Volunteer model instance.

    Raises:
        AlreadyExistsError: If a user with the same username or email already exists.
    """
    # Ensure user_type is VOLUNTEER
    user_data = user_in.model_dump()
    user_data["user_type"] = UserType.VOLUNTEER
    user_create = UserCreate.model_validate(user_data)

    # Create the user first
    db_user = user_service.create_user(session, user_create)

    # Create volunteer profile linked to the user
    db_volunteer = Volunteer.model_validate(
        volunteer_in, update={"id_user": db_user.id_user}
    )

    session.add(db_volunteer)
    session.commit()
    session.refresh(db_volunteer)

    return db_volunteer


def get_volunteer(session: Session, volunteer_id: int) -> Volunteer | None:
    """
    Retrieve a volunteer by its primary key and load the related user.

    Parameters:
        volunteer_id (int): The volunteer's primary key.

    Returns:
        The Volunteer with its user relationship loaded, or None if not found.
    """
    statement = (
        select(Volunteer)
        .where(Volunteer.id_volunteer == volunteer_id)
        .options(selectinload(Volunteer.user))  # type: ignore
    )
    return session.exec(statement).first()


def get_volunteer_by_user_id(session: Session, user_id: int) -> Volunteer | None:
    """
    Retrieve the Volunteer record associated with a given user ID.

    The returned Volunteer will include the related `user` relationship if found.

    Returns:
        The Volunteer for the provided user ID, or `None` if no matching volunteer exists.
    """
    statement = (
        select(Volunteer)
        .where(Volunteer.id_user == user_id)
        .options(selectinload(Volunteer.user))  # type: ignore
    )
    return session.exec(statement).first()


def get_volunteers(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[VolunteerPublic]:
    """
    Retrieve a paginated list of volunteers with embedded public user data and precomputed mission counts.

    Parameters:
        offset (int): Number of records to skip.
        limit (int): Maximum number of records to return.

    Returns:
        list[VolunteerPublic]: VolunteerPublic objects for the requested page, each containing public user information and active/finished mission counts.
    """
    statement = (
        select(Volunteer)
        .options(selectinload(Volunteer.user))  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    volunteers = list(session.exec(statement).all())

    if not volunteers:
        return []

    # Batch compute mission counts
    volunteer_ids = [v.id_volunteer for v in volunteers if v.id_volunteer is not None]
    counts_map = _compute_mission_counts_batch(session, volunteer_ids)

    return to_volunteer_public_from_batch(volunteers, counts_map)


def update_volunteer(
    session: Session, volunteer_id: int, volunteer_update: VolunteerUpdate
) -> Volunteer:
    """
    Update an existing volunteer's profile and their linked user account.

    Parameters:
        volunteer_id (int): Primary key of the volunteer to update.
        volunteer_update (VolunteerUpdate): Partial update data; only provided fields will be applied.
            May include volunteer attributes (e.g., name, phone) and user attributes (`email`, `password`).

    Returns:
        Volunteer: The updated Volunteer instance with its user relationship loaded.

    Raises:
        NotFoundError: If no volunteer exists with the given `volunteer_id`.
    """
    db_volunteer = get_volunteer(session, volunteer_id)
    if not db_volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    # Convert update model to dict, excluding unset fields
    update_data = volunteer_update.model_dump(exclude_unset=True)

    # Separate user fields from volunteer fields
    user_fields = {"email", "password"}
    user_data = {k: v for k, v in update_data.items() if k in user_fields}
    volunteer_data = {k: v for k, v in update_data.items() if k not in user_fields}

    # Update volunteer fields
    for key, value in volunteer_data.items():
        setattr(db_volunteer, key, value)

    # Update user fields if any were provided
    if user_data:
        user_update = UserUpdate.model_validate(user_data)
        user_service.update_user(session, db_volunteer.id_user, user_update)

    session.add(db_volunteer)
    session.commit()
    session.refresh(db_volunteer)

    return db_volunteer


def delete_volunteer(session: Session, volunteer_id: int) -> None:
    """
    Remove a volunteer and their associated user account.

    Parameters:
        volunteer_id (int): Primary key of the volunteer to remove.

    Raises:
        NotFoundError: If no volunteer exists with the given `volunteer_id`.
    """
    db_volunteer = get_volunteer(session, volunteer_id)
    if not db_volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    user_id = db_volunteer.id_user

    # Delete volunteer first (child), then user (parent)
    session.delete(db_volunteer)

    # Delete associated user
    user_service.delete_user(session, user_id)

    session.commit()


def get_volunteer_missions(
    session: Session,
    volunteer_id: int,
    *,
    target_date: date | None = None,
) -> list[MissionPublic]:
    """
    Get missions a volunteer is approved to engage in, optionally filtered to those active on a specific date.

    Only engagements with state `ProcessingStatus.APPROVED` are considered. If `target_date` is provided, only missions where `date_start <= target_date <= date_end` are returned.

    Parameters:
        volunteer_id (int): Primary key of the volunteer whose missions to retrieve.
        target_date (date | None): Optional date to filter missions to those active on that date.

    Returns:
        list[MissionPublic]: Missions matching the criteria.
    """
    statement = (
        select(Mission)
        .join(Engagement, Engagement.id_mission == Mission.id_mission)  # type: ignore[arg-type]
        .where(
            Engagement.id_volunteer == volunteer_id,
            Engagement.state == ProcessingStatus.APPROVED,
        )
    )

    if target_date is not None:
        statement = statement.where(
            Mission.date_start <= target_date,
            Mission.date_end >= target_date,
        )

    missions = session.exec(statement).all()
    return [MissionPublic.model_validate(m) for m in missions]


# Favorite operations


def get_favorite_missions(session: Session, volunteer_id: int) -> list[MissionPublic]:
    """
    Return a volunteer's favorited missions ordered by most recently favorited.

    Parameters:
        volunteer_id (int): Primary key of the volunteer.

    Returns:
        list[MissionPublic]: Favorited missions for the volunteer, ordered by favorite creation time descending (most recent first).
    """
    statement = (
        select(Mission)
        .join(Favorite, Favorite.id_mission == Mission.id_mission)  # type: ignore[arg-type]
        .where(Favorite.id_volunteer == volunteer_id)
        .order_by(Favorite.created_at.desc())  # type: ignore[union-attr]
    )
    missions = session.exec(statement).all()
    return [MissionPublic.model_validate(m) for m in missions]


def add_favorite_mission(session: Session, volunteer_id: int, mission_id: int) -> None:
    """
    Add a mission to a volunteer's favorites.

    Parameters:
        session (Session): Database session.
        volunteer_id (int): Primary key of the volunteer.
        mission_id (int): Primary key of the mission.

    Raises:
        NotFoundError: If the mission or volunteer does not exist.
        AlreadyExistsError: If the volunteer has already favorited the mission.
    """
    # Check mission exists
    mission = session.exec(
        select(Mission).where(Mission.id_mission == mission_id)
    ).first()
    if not mission:
        raise NotFoundError("Mission", mission_id)

    # Check volunteer exists
    volunteer = session.exec(
        select(Volunteer).where(Volunteer.id_volunteer == volunteer_id)
    ).first()
    if not volunteer:
        raise NotFoundError("Volunteer", volunteer_id)

    # Check if already favorited
    existing = session.exec(
        select(Favorite).where(
            Favorite.id_volunteer == volunteer_id,
            Favorite.id_mission == mission_id,
        )
    ).first()
    if existing:
        raise AlreadyExistsError("Favorite", "mission", mission_id)

    # Add favorite
    favorite = Favorite(id_volunteer=volunteer_id, id_mission=mission_id)
    session.add(favorite)
    session.commit()


def remove_favorite_mission(
    session: Session, volunteer_id: int, mission_id: int
) -> None:
    """
    Removes a mission from a volunteer's favorites.

    Raises:
        NotFoundError: If no favorite exists for the given volunteer and mission.
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.id_volunteer == volunteer_id,
            Favorite.id_mission == mission_id,
        )
    ).first()
    if not favorite:
        raise NotFoundError("Favorite", mission_id)

    session.delete(favorite)
    session.commit()
