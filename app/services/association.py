"""Association service module for CRUD operations."""

import re
from datetime import date

from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.models.association import (
    Association,
    AssociationCreate,
    AssociationUpdate,
    AssociationPublic,
)
from app.models.user import UserCreate, UserUpdate, UserPublic
from app.models.mission import Mission
from app.models.enums import UserType
from app.exceptions import NotFoundError, ValidationError
from app.services import user as user_service


def validate_rna_code(rna_code: str) -> None:
    """
    Validate the format of the RNA code (French association registry).
    Format: 'W' followed by 9 digits (e.g., W123456789).
    """
    pattern = r"^W\d{9}$"
    if not re.match(pattern, rna_code):
        raise ValidationError(
            f"Invalid RNA code format: {rna_code}. Must be 'W' followed by 9 digits.",
            field="rna_code",
        )


def _compute_mission_counts(session: Session, association_id: int) -> tuple[int, int]:
    """
    Compute the active and finished mission counts for an association.

    Active missions: Missions where date_end >= today.
    Finished missions: Missions where date_end < today.

    Returns:
        tuple[int, int]: (active_missions_count, finished_missions_count)
    """
    today = date.today()

    # Count active missions
    active_stmt = select(func.count()).where(
        Mission.id_asso == association_id,
        Mission.date_end >= today,
    )
    active_count = session.exec(active_stmt).one()

    # Count finished missions
    finished_stmt = select(func.count()).where(
        Mission.id_asso == association_id,
        Mission.date_end < today,
    )
    finished_count = session.exec(finished_stmt).one()

    return active_count, finished_count


def _compute_mission_counts_batch(
    session: Session, association_ids: list[int]
) -> dict[int, tuple[int, int]]:
    """
    Compute active and finished mission counts for the given associations.

    Parameters:
        session (Session): Database session used to execute the query.
        association_ids (list[int]): List of association IDs to compute counts for.

    Returns:
        dict[int, tuple[int, int]]: Mapping from association_id to a tuple (active_count, finished_count).
    """
    if not association_ids:
        return {}

    today = date.today()

    # Base query for missions owned by these associations
    base_query = select(Mission.id_asso, Mission.date_end).where(  # type: ignore
        Mission.id_asso.in_(association_ids)  # type: ignore
    )

    results = session.exec(base_query).all()

    # Aggregate in Python
    counts: dict[int, list[int]] = {aid: [0, 0] for aid in association_ids}

    for aid, end_date in results:
        # aid might be None in database if nullable, but our query filtered on in_(association_ids)
        if aid is not None and aid in counts:
            if end_date >= today:
                counts[aid][0] += 1  # Active
            else:
                counts[aid][1] += 1  # Finished

    return {k: (v[0], v[1]) for k, v in counts.items()}


def to_association_public(
    session: Session, association: Association
) -> AssociationPublic:
    """
    Convert an Association database model into an AssociationPublic response with mission counts and embedded user.

    Parameters:
        association (Association): Association model; must have `id_asso` set.

    Returns:
        AssociationPublic: Public representation containing association fields, mission counts, and user.
    """
    assert association.id_asso is not None
    active_count, finished_count = _compute_mission_counts(session, association.id_asso)

    user_public = None
    if association.user:
        user_public = UserPublic.model_validate(association.user)

    return AssociationPublic(
        **association.model_dump(exclude={"user", "missions", "documents"}),
        active_missions_count=active_count,
        finished_missions_count=finished_count,
        user=user_public,
    )


def to_association_public_from_batch(
    associations: list[Association], counts_map: dict[int, tuple[int, int]]
) -> list[AssociationPublic]:
    """
    Convert Association models to AssociationPublic objects using a provided map of mission counts.

    Parameters:
        associations: Iterable of Association database models to convert.
        counts_map: Mapping from association id to a tuple (active_count, finished_count).

    Returns:
        list[AssociationPublic]: Converted AssociationPublic objects.
    """
    results = []
    for association in associations:
        assert association.id_asso is not None
        active_count, finished_count = counts_map.get(association.id_asso, (0, 0))

        user_public = None
        if association.user:
            user_public = UserPublic.model_validate(association.user)

        results.append(
            AssociationPublic(
                **association.model_dump(exclude={"user", "missions", "documents"}),
                active_missions_count=active_count,
                finished_missions_count=finished_count,
                user=user_public,
            )
        )
    return results


def create_association(
    session: Session, user_in: UserCreate, association_in: AssociationCreate
) -> Association:
    """
    Create a new association with an associated user account.

    Validates RNA code format.
    Creates a User with user_type set to ASSOCIATION, then creates the Association
    profile linked to that user.

    Parameters:
        session: Database session.
        user_in: User creation data.
        association_in: Association profile data.

    Returns:
        Association: The created Association model instance with user relationship loaded.

    Raises:
        ValidationError: If RNA code format is invalid.
        AlreadyExistsError: If a user with the same username or email already exists.
    """
    # Validate RNA code
    validate_rna_code(association_in.rna_code)

    # Ensure user_type is ASSOCIATION
    user_data = user_in.model_dump()
    user_data["user_type"] = UserType.ASSOCIATION
    user_create = UserCreate.model_validate(user_data)

    # Create the user first
    db_user = user_service.create_user(session, user_create)

    # Create association profile linked to the user
    db_association = Association.model_validate(
        association_in, update={"id_user": db_user.id_user}
    )

    session.add(db_association)
    session.commit()
    session.refresh(db_association)

    return db_association


def get_association(session: Session, association_id: int) -> Association | None:
    """
    Retrieve an association by ID with user relationship loaded.

    Parameters:
        session: Database session.
        association_id: The association's primary key.

    Returns:
        Association | None: The association record with user loaded, or None if not found.
    """
    statement = (
        select(Association)
        .where(Association.id_asso == association_id)
        .options(selectinload(Association.user))  # type: ignore
    )
    return session.exec(statement).first()


def get_association_by_user_id(session: Session, user_id: int) -> Association | None:
    """
    Retrieve the Association record associated with the given user ID.

    Parameters:
        user_id (int): The primary key of the user to look up.

    Returns:
        The Association instance linked to the user, or None if no association exists.
    """
    statement = (
        select(Association)
        .where(Association.id_user == user_id)
        .options(selectinload(Association.user))  # type: ignore
    )
    return session.exec(statement).first()


def get_associations(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[AssociationPublic]:
    """
    Retrieve a paginated list of associations with user relationships loaded.

    Optimized to fetch mission counts in a single batch query.

    Parameters:
        session: Database session.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[AssociationPublic]: Association records for the requested page.
    """
    statement = (
        select(Association)
        .options(selectinload(Association.user))  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    associations = list(session.exec(statement).all())

    if not associations:
        return []

    # Batch compute mission counts
    association_ids = [a.id_asso for a in associations if a.id_asso is not None]
    counts_map = _compute_mission_counts_batch(session, association_ids)

    return to_association_public_from_batch(associations, counts_map)


def update_association(
    session: Session, association_id: int, association_update: AssociationUpdate
) -> Association:
    """
    Update an existing association's profile and associated user account.

    Validates RNA code if it is being updated.

    Parameters:
        session: Database session.
        association_id: Primary key of the association to update.
        association_update: Partial update data.

    Returns:
        Association: The updated association record with user relationship loaded.

    Raises:
        NotFoundError: If no association exists with the given association_id.
        ValidationError: If new RNA code format is invalid.
        AlreadyExistsError: If email update causes a uniqueness conflict.
    """
    db_association = get_association(session, association_id)
    if not db_association:
        raise NotFoundError("Association", association_id)

    # Convert update model to dict, excluding unset fields
    update_data = association_update.model_dump(exclude_unset=True)

    # Separate user fields from association fields
    user_fields = {"email", "password"}
    user_data = {k: v for k, v in update_data.items() if k in user_fields}
    association_data = {k: v for k, v in update_data.items() if k not in user_fields}

    # Validate RNA code if present in update
    if "rna_code" in association_data and association_data["rna_code"]:
        validate_rna_code(association_data["rna_code"])

    # Update association fields
    for key, value in association_data.items():
        setattr(db_association, key, value)

    # Update user fields if any were provided
    if user_data:
        user_update = UserUpdate.model_validate(user_data)
        user_service.update_user(session, db_association.id_user, user_update)

    session.add(db_association)
    session.commit()
    session.refresh(db_association)
    # Force reload of user relationship to ensure it reflects changes
    session.expire(db_association, ["user"])

    return db_association


async def delete_association(session: Session, association_id: int) -> None:
    """
    Delete an association and their associated user account.

    Sends email notification to the user before deletion.

    Parameters:
        session: Database session.
        association_id: Primary key of the association to delete.

    Raises:
        NotFoundError: If no association exists with the given association_id.
    """
    db_association = get_association(session, association_id)
    if not db_association:
        raise NotFoundError("Association", association_id)

    user_id = db_association.id_user

    # Delete association first (child), then user (parent)
    session.delete(db_association)

    # Delete associated user (sends email notification)
    await user_service.delete_user(session, user_id)

    session.commit()
