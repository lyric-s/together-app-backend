"""Auth profile response models for /auth/me endpoint."""

from typing import Literal, Union
from sqlmodel import SQLModel
from app.models.user import UserPublic
from app.models.volunteer import VolunteerPublic
from app.models.association import AssociationPublic
from app.models.admin import AdminPublic


class VolunteerProfile(SQLModel):
    """Profile response for volunteer users."""

    user_type: Literal["volunteer"] = "volunteer"
    user: UserPublic
    profile: VolunteerPublic


class AssociationProfile(SQLModel):
    """Profile response for association users."""

    user_type: Literal["association"] = "association"
    user: UserPublic
    profile: AssociationPublic


class AdminProfile(SQLModel):
    """Profile response for admin users."""

    user_type: Literal["admin"] = "admin"
    profile: AdminPublic


# Union type for response model
AuthProfile = Union[VolunteerProfile, AssociationProfile, AdminProfile]
