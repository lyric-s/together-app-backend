"""Admin service module for CRUD operations."""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.admin import Admin, AdminCreate, AdminUpdate
from app.core.password import get_password_hash


def create_admin(session: Session, admin_in: AdminCreate) -> Admin:
    """
    Create a new admin with hashed password.

    Args:
        session: Database session
        admin_in: Admin creation data including plaintext password

    Returns:
        Admin: The created admin record

    Raises:
        HTTPException: 400 if username or email already exists
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )
    session.refresh(db_admin)
    return db_admin


def get_admin(session: Session, admin_id: int) -> Admin | None:
    """
    Retrieve an admin by ID.

    Args:
        session: Database session
        admin_id: The admin's primary key

    Returns:
        Admin | None: The admin record or None if not found
    """
    statement = select(Admin).where(Admin.id_admin == admin_id)
    return session.exec(statement).first()


def get_admin_by_username(session: Session, username: str) -> Admin | None:
    """
    Retrieve an admin by username.

    Args:
        session: Database session
        username: The admin's username

    Returns:
        Admin | None: The admin record or None if not found
    """
    statement = select(Admin).where(Admin.username == username)
    return session.exec(statement).first()


def get_admin_by_email(session: Session, email: str) -> Admin | None:
    """
    Retrieve an admin by email.

    Args:
        session: Database session
        email: The admin's email address

    Returns:
        Admin | None: The admin record or None if not found
    """
    statement = select(Admin).where(Admin.email == email)
    return session.exec(statement).first()


def get_admins(session: Session, *, offset: int = 0, limit: int = 100) -> list[Admin]:
    """
    Retrieve a paginated list of admins.

    Args:
        session: Database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)

    Returns:
        list[Admin]: List of admin records
    """
    statement = select(Admin).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_admin(session: Session, admin_id: int, admin_update: AdminUpdate) -> Admin:
    """
    Update an existing admin's information.

    Args:
        session: Database session
        admin_id: The admin's primary key
        admin_update: Partial update data (only provided fields will be updated)

    Returns:
        Admin: The updated admin record

    Raises:
        HTTPException: 404 if admin not found, 400 if email already exists
    """
    db_admin = get_admin(session, admin_id)
    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    session.refresh(db_admin)
    return db_admin


def delete_admin(session: Session, admin_id: int) -> None:
    """
    Delete an admin by ID.

    Args:
        session: Database session
        admin_id: The admin's primary key

    Raises:
        HTTPException: 404 if admin not found
    """
    db_admin = get_admin(session, admin_id)
    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    session.delete(db_admin)
    session.commit()
