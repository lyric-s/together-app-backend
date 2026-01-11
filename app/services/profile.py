"""Profile resolution service to break circular dependencies."""

from sqlmodel import Session
from app.models.user import User, UserPublic
from app.models.enums import UserType
from app.exceptions import NotFoundError, ValidationError
from app.utils.validation import ensure_id
from app.services import volunteer as volunteer_service
from app.services import association as association_service


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
