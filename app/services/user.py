"""User service module for CRUD operations."""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserCreate, UserUpdate
from app.core.password import get_password_hash
from app.exceptions import NotFoundError, AlreadyExistsError


def create_user(session: Session, user_in: UserCreate) -> User:
    """
    Create a new user with hashed password.

    Args:
        session: Database session
        user_in: User creation data including plaintext password

    Returns:
        User: The created user record

    Raises:
        AlreadyExistsError: If username or email already exists
    """
    hashed_password = get_password_hash(user_in.password)

    db_user = User.model_validate(user_in, update={"hashed_password": hashed_password})

    session.add(db_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("User", "username or email", user_in.username)
    session.refresh(db_user)
    return db_user


def get_user(session: Session, user_id: int) -> User | None:
    """
    Retrieve a user by ID.

    Args:
        session: Database session
        user_id: The user's primary key

    Returns:
        User | None: The user record or None if not found
    """
    statement = select(User).where(User.id_user == user_id)
    return session.exec(statement).first()


def get_user_by_username(session: Session, username: str) -> User | None:
    """
    Retrieve a user by username.

    Args:
        session: Database session
        username: The user's username

    Returns:
        User | None: The user record or None if not found
    """
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_user_by_email(session: Session, email: str) -> User | None:
    """
    Retrieve a user by email.

    Args:
        session: Database session
        email: The user's email address

    Returns:
        User | None: The user record or None if not found
    """
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_users(session: Session, *, offset: int = 0, limit: int = 100) -> list[User]:
    """
    Retrieve a paginated list of users.

    Args:
        session: Database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)

    Returns:
        list[User]: List of user records
    """
    statement = select(User).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_user(session: Session, user_id: int, user_update: UserUpdate) -> User:
    """
    Update an existing user's information.

    Args:
        session: Database session
        user_id: The user's primary key
        user_update: Partial update data (only provided fields will be updated)

    Returns:
        User: The updated user record

    Raises:
        NotFoundError: If user not found
        AlreadyExistsError: If username or email already exists
    """
    db_user = get_user(session, user_id)
    if not db_user:
        raise NotFoundError("User", user_id)

    # Convert update model to dict, excluding unset fields
    user_data = user_update.model_dump(exclude_unset=True)

    # Handle password hashing if password is being updated
    if "password" in user_data and user_data["password"] is not None:
        hashed_password = get_password_hash(user_data["password"])
        user_data["hashed_password"] = hashed_password
        del user_data["password"]

    # Update fields
    for key, value in user_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("User", "email", user_update.email or "unknown")
    session.refresh(db_user)
    return db_user


def delete_user(session: Session, user_id: int) -> None:
    """
    Delete a user by ID.

    Args:
        session: Database session
        user_id: The user's primary key

    Raises:
        NotFoundError: If user not found
    """
    db_user = get_user(session, user_id)
    if not db_user:
        raise NotFoundError("User", user_id)

    session.delete(db_user)
    session.commit()
