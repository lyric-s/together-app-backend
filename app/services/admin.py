"""Admin service module for CRUD operations."""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.admin import Admin, AdminCreate, AdminUpdate
from app.core.password import get_password_hash
from app.exceptions import NotFoundError, AlreadyExistsError


def create_admin(session: Session, admin_in: AdminCreate) -> Admin:
    """
    Create a new admin and persist it with a hashed password.

    Parameters:
        session (Session): Database session.
        admin_in (AdminCreate): Admin creation data; must include plaintext `password`.

    Returns:
        Admin: The created admin record.

    Raises:
        AlreadyExistsError: If username or email already exists.
    """
    hashed_password = get_password_hash(admin_in.password)

    db_admin = Admin.model_validate(
        admin_in, update={"hashed_password": hashed_password}
    )

    session.add(db_admin)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("Admin", "username or email", admin_in.username)
    session.refresh(db_admin)
    return db_admin


def get_admin(session: Session, admin_id: int) -> Admin | None:
    """
    Retrieve an admin by ID.

    Parameters:
        admin_id (int): Primary key of the admin to retrieve.

    Returns:
        Admin | None: `Admin` if found, `None` otherwise.
    """
    statement = select(Admin).where(Admin.id_admin == admin_id)
    return session.exec(statement).first()


def get_admin_by_username(session: Session, username: str) -> Admin | None:
    """
    Retrieve an admin by username.

    Returns:
        `Admin` instance matching the username, `None` if no matching admin is found.
    """
    statement = select(Admin).where(Admin.username == username)
    return session.exec(statement).first()


def get_admin_by_email(session: Session, email: str) -> Admin | None:
    """
    Retrieve an admin by email.

    Parameters:
        email (str): The email address to search for.

    Returns:
        Admin | None: `Admin` if a record with the given email exists, `None` otherwise.
    """
    statement = select(Admin).where(Admin.email == email)
    return session.exec(statement).first()


def get_admins(session: Session, *, offset: int = 0, limit: int = 100) -> list[Admin]:
    """
    Retrieve a paginated list of admin records.

    Parameters:
        offset (int): Number of records to skip. Defaults to 0.
        limit (int): Maximum number of records to return. Defaults to 100.

    Returns:
        admins (list[Admin]): List of Admin instances for the requested page.
    """
    statement = select(Admin).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_admin(session: Session, admin_id: int, admin_update: AdminUpdate) -> Admin:
    """
    Apply partial updates to an existing admin and persist the changes.

    Only fields present on `admin_update` are applied. If `password` is provided it will be hashed and stored as `hashed_password`.

    Parameters:
        admin_update (AdminUpdate): Partial update data; unset fields are ignored.

    Returns:
        Admin: The updated Admin instance.

    Raises:
        NotFoundError: If no admin exists with the given `admin_id`.
        AlreadyExistsError: If persistence fails due to a uniqueness constraint (for example, duplicate email).
    """
    db_admin = get_admin(session, admin_id)
    if not db_admin:
        raise NotFoundError("Admin", admin_id)

    # Convert update model to dict, excluding unset fields
    admin_data = admin_update.model_dump(exclude_unset=True)

    # Hashing password if provided
    extra_data = {}
    if "password" in admin_data:
        password = admin_data.pop("password")
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password

    db_admin.sqlmodel_update(admin_data, update=extra_data)
    session.add(db_admin)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("Admin", "email", admin_update.email or "unknown")
    session.refresh(db_admin)
    return db_admin


def delete_admin(session: Session, admin_id: int) -> None:
    """
    Delete an admin by ID.

    Args:
        session: Database session
        admin_id: The admin's primary key

    Raises:
        NotFoundError: If admin not found
    """
    db_admin = get_admin(session, admin_id)
    if not db_admin:
        raise NotFoundError("Admin", admin_id)

    session.delete(db_admin)
    session.commit()


def get_admin_profile(admin: Admin) -> dict:
    """
    Get admin profile (no user relationship, admins are separate table).

    Args:
        admin: Admin instance

    Returns:
        dict: Profile dictionary containing user_type and profile
    """
    from app.models.admin import AdminPublic

    admin_public = AdminPublic.model_validate(admin)
    return {"user_type": "admin", "profile": admin_public}
