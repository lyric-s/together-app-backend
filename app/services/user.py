"""User service module for CRUD operations."""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserCreate, UserUpdate
from app.core.password import get_password_hash
from app.exceptions import NotFoundError, AlreadyExistsError


def create_user(session: Session, user_in: UserCreate) -> User:
    """
    Create and persist a new user with a hashed password.
    
    Parameters:
        user_in (UserCreate): User creation data; must include a plaintext `password`. The plaintext password will be hashed before storage.
    
    Returns:
        User: The created User model instance.
    
    Raises:
        AlreadyExistsError: If a user with the same username or email already exists.
    """
    hashed_password = get_password_hash(user_in.password)

    db_user = User.model_validate(user_in, update={"hashed_password": hashed_password})

    session.add(db_user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("User", "unique field", "username or email")
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

    Parameters:
        username (str): The username to look up.

    Returns:
        User | None: `User` if a matching record exists, `None` otherwise.
    """
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_user_by_email(session: Session, email: str) -> User | None:
    """
    Retrieve a user by email.

    Parameters:
        session: Database session used to execute the query.
        email: Email address to look up.

    Returns:
        The `User` instance matching the given email, or `None` if no match is found.
    """
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_users(session: Session, *, offset: int = 0, limit: int = 100) -> list[User]:
    """
    Retrieve a paginated list of users.

    Returns:
        list[User]: User records for the requested page defined by offset and limit.
    """
    statement = select(User).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_user(session: Session, user_id: int, user_update: UserUpdate) -> User:
    """
    Update an existing user's information.

    Parameters:
        user_id (int): Primary key of the user to update.
        user_update (UserUpdate): Partial update data; only provided fields will be applied. If `password` is provided, it will be hashed and stored on the user as `hashed_password`.

    Returns:
        User: The updated user record.

    Raises:
        NotFoundError: If no user exists with the given `user_id`.
        AlreadyExistsError: If updating causes a uniqueness conflict (for example, duplicate username or email).
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
        session.flush()
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("User", "unique field", "one of the updated fields")
    session.refresh(db_user)
    return db_user


def delete_user(session: Session, user_id: int) -> None:
    """
    Delete the user with the given primary key from the database.
    
    Parameters:
        user_id (int): Primary key of the user to delete.
    
    Raises:
        NotFoundError: If no user exists with the given user_id.
    """
    db_user = get_user(session, user_id)
    if not db_user:
        raise NotFoundError("User", user_id)

    session.delete(db_user)
    session.flush()