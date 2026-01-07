"""Volunteer service module for CRUD operations."""

from datetime import date

from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

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
    Compute the active and finished mission counts for a volunteer.

    Active missions: Approved engagements where mission.date_end >= today.
    Finished missions: Approved engagements where mission.date_end < today.

    Returns:
        tuple[int, int]: (active_missions_count, finished_missions_count)
    """
    today = date.today()

    # Count active missions (approved engagements with ongoing missions)
    active_stmt = (
        select(func.count())
        .select_from(Engagement)
        .join(Mission, Engagement.id_mission == Mission.id_mission)  # type: ignore[arg-type]
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
        .join(Mission, Engagement.id_mission == Mission.id_mission)  # type: ignore[arg-type]
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

    Active counts include approved engagements whose mission end date is greater than or equal to today; finished counts include approved engagements whose mission end date is before today.

    Parameters:
        session (Session): Database session used to execute the query.
        volunteer_ids (list[int]): List of volunteer IDs to compute counts for.

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
    Convert a Volunteer database model into a VolunteerPublic response with mission counts and embedded user.

    Parameters:
        volunteer (Volunteer): Volunteer model; must have `id_volunteer` set. The related `user` (if present) will be converted to `UserPublic`.

    Returns:
        VolunteerPublic: Public representation containing volunteer fields (excluding internal relations), `active_missions_count`, `finished_missions_count`, and `user` when available.
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
    Convert Volunteer models to VolunteerPublic objects using a provided map of mission counts.

    Parameters:
        volunteers: Iterable of Volunteer database models to convert.
        counts_map: Mapping from volunteer id to a tuple (active_count, finished_count) used to populate mission counts; missing ids default to (0, 0).

    Returns:
        list[VolunteerPublic]: Converted VolunteerPublic objects with `active_missions_count`, `finished_missions_count`, and an embedded `user` when present.
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
    Create a new volunteer with an associated user account.

    Creates a User with user_type set to VOLUNTEER, then creates the Volunteer
    profile linked to that user.

    Parameters:
        session: Database session.
        user_in: User creation data (username, email, password).
        volunteer_in: Volunteer profile data (name, phone, birthdate, etc.).

    Returns:
        Volunteer: The created Volunteer model instance with user relationship loaded.

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
    Retrieve a volunteer by ID with user relationship loaded.

    Parameters:
        session: Database session.
        volunteer_id: The volunteer's primary key.

    Returns:
        Volunteer | None: The volunteer record with user loaded, or None if not found.
    """
    statement = (
        select(Volunteer)
        .where(Volunteer.id_volunteer == volunteer_id)
        .options(selectinload(Volunteer.user))  # type: ignore
    )
    return session.exec(statement).first()


def get_volunteer_by_user_id(session: Session, user_id: int) -> Volunteer | None:
    """
    Retrieve the Volunteer record associated with the given user ID.

    Parameters:
        user_id (int): The primary key of the user to look up.

    Returns:
        The Volunteer instance linked to the user, or None if no volunteer exists.
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
    Retrieve a paginated list of volunteers with user relationships loaded.

    Optimized to fetch mission counts in a single batch query to avoid N+1.

    Parameters:
        session: Database session.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[VolunteerPublic]: Volunteer records for the requested page.
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
    Update an existing volunteer's profile and associated user account.

    Parameters:
        session: Database session.
        volunteer_id: Primary key of the volunteer to update.
        volunteer_update: Partial update data; only provided fields will be applied.
            Includes volunteer fields (name, phone, etc.) and user fields (email, password).

    Returns:
        Volunteer: The updated volunteer record with user relationship loaded.

    Raises:
        NotFoundError: If no volunteer exists with the given volunteer_id.
        AlreadyExistsError: If email update causes a uniqueness conflict.
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
    Delete a volunteer and their associated user account.

    Parameters:
        session: Database session.
        volunteer_id: Primary key of the volunteer to delete.

    Raises:
        NotFoundError: If no volunteer exists with the given volunteer_id.
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
    Retrieve missions for a volunteer, optionally filtered by date.

    Returns approved missions where the volunteer is engaged. If target_date is
    provided, only returns missions where date_start <= target_date <= date_end.

    Parameters:
        session: Database session.
        volunteer_id: The volunteer's primary key.
        target_date: Optional date to filter missions (returns missions active on this date).

    Returns:
        list[MissionPublic]: List of missions matching the criteria.
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
    Retrieve all missions a volunteer has marked as favorites, ordered by when they were favorited (newest first).

    Parameters:
        session: Database session used for the query.
        volunteer_id (int): Primary key of the volunteer whose favorites to fetch.

    Returns:
        list[MissionPublic]: Favorited missions as `MissionPublic` objects ordered by Favorite.created_at descending.
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
    Add a mission to volunteer's favorites.

    Parameters:
        session: Database session.
        volunteer_id: The volunteer's primary key.
        mission_id: The mission's primary key.

    Raises:
        NotFoundError: If the mission or volunteer doesn't exist.
        AlreadyExistsError: If the mission is already favorited.
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
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Handle rare race where another transaction inserted the same favorite
        raise AlreadyExistsError("Favorite", "mission", mission_id)


def remove_favorite_mission(
    session: Session, volunteer_id: int, mission_id: int
) -> None:
    """
    Remove a mission from a volunteer's favorites.

    Raises:
        NotFoundError: If no favorite exists linking the volunteer and mission.
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
