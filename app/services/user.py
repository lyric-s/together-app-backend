"""User service module for CRUD operations."""

import secrets
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserCreate, UserUpdate
from app.core.password import get_password_hash, get_token_hash
from app.core.config import get_settings
from app.exceptions import NotFoundError, AlreadyExistsError, InvalidTokenError
from app.utils.validation import ensure_id


def create_user(session: Session, user_in: UserCreate) -> User:
    """
    Create and persist a new user with a hashed password.

    Parameters:
        user_in (UserCreate): User creation data; must include a plaintext `password` and other user fields.

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


async def delete_user(session: Session, user_id: int) -> None:
    """
    Delete the user identified by `user_id` and send notification email.

    Sends email notification to the user before deletion informing them
    that their account has been deleted by an administrator.

    Parameters:
        user_id (int): Primary key of the user to delete.

    Raises:
        NotFoundError: If no user exists with the given `user_id`.
    """
    db_user = get_user(session, user_id)
    if not db_user:
        raise NotFoundError("User", user_id)

    # Send email notification before deletion
    from app.services.email import send_notification_email
    import logging

    try:
        await send_notification_email(
            template_name="account_deleted",
            recipient_email=db_user.email,
            context={"username": db_user.username},
        )
    except Exception as e:
        # Log error but don't fail the deletion
        logging.error(f"Failed to send account deletion email: {e}")

    session.delete(db_user)
    session.flush()


def create_password_reset_token(session: Session, email: str) -> tuple[User, str]:
    """
    Generate and store a password reset token for a user.

    Args:
        session: Database session
        email: User's email address

    Returns:
        tuple[User, str]: The user and the plain reset token (to send via email)

    Raises:
        NotFoundError: If no user exists with the given email
    """
    user = get_user_by_email(session, email)
    if not user:
        raise NotFoundError("User", email)

    # Generate a URL-safe token (~64 characters)
    reset_token = secrets.token_urlsafe(48)

    # Hash and store the token
    user.password_reset_token = get_token_hash(reset_token)

    # Set expiration time
    settings = get_settings()
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    session.add(user)
    session.flush()
    session.refresh(user)
    return user, reset_token


def reset_password_with_token(session: Session, token: str, new_password: str) -> User:
    """
    Reset a user's password using a password reset token.

    Args:
        session: Database session
        token: Plain password reset token (from email)
        new_password: New password to set

    Returns:
        User: The updated user

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    hashed_token = get_token_hash(token)
    user = session.exec(
        select(User).where(User.password_reset_token == hashed_token)
    ).first()

    if not user or not user.password_reset_expires:
        raise InvalidTokenError("Invalid password reset token")

    # Check if token has expired
    if datetime.now(timezone.utc) > user.password_reset_expires:
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_expires = None
        session.flush()
        raise InvalidTokenError("Password reset token has expired")

    # Update password and clear reset token fields
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    # Force re-login by clearing refresh token
    user.hashed_refresh_token = None

    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def get_user_with_profile(session: Session, user: User) -> dict:
    """
    Get user profile for volunteers and associations.

    Args:
        session: Database session
        user: User instance

    Returns:
        dict: Profile dictionary containing user_type, user, and profile

    Raises:
        NotFoundError: If the profile doesn't exist for the user
        ValidationError: If user type is invalid
    """
    from app.models.user import UserPublic
    from app.models.enums import UserType
    from app.services import volunteer as volunteer_service
    from app.services import association as association_service
    from app.exceptions import ValidationError

    user_id = ensure_id(user.id_user, "User")
    user_public = UserPublic.model_validate(user)

    if user.user_type == UserType.VOLUNTEER:
        volunteer = volunteer_service.get_volunteer_by_user_id(session, user_id)
        if not volunteer:
            raise NotFoundError("Volunteer profile", user_id)
        volunteer_public = volunteer_service.to_volunteer_public(session, volunteer)
        return {
            "user_type": "volunteer",
            "user": user_public,
            "profile": volunteer_public,
        }

    elif user.user_type == UserType.ASSOCIATION:
        association = association_service.get_association_by_user_id(session, user_id)
        if not association:
            raise NotFoundError("Association profile", user_id)
        association_public = association_service.to_association_public(
            session, association
        )
        return {
            "user_type": "association",
            "user": user_public,
            "profile": association_public,
        }

    raise ValidationError(f"Invalid user type: {user.user_type}")
