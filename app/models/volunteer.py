from datetime import date
from typing import TYPE_CHECKING
from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Relationship
from app.models.assign import Assign
from app.models.engagement import Engagement
from app.models.user import UserPublic, EMAIL_MAX_LENGTH, PASSWORD_MIN_LENGTH

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.badge import Badge
    from app.models.mission import Mission

# Field constraints
VOLUNTEER_NAME_MAX_LENGTH = 50
VOLUNTEER_PHONE_MAX_LENGTH = 20
VOLUNTEER_ZIP_MAX_LENGTH = 20
VOLUNTEER_SKILLS_MAX_LENGTH = 500
VOLUNTEER_BIO_MAX_LENGTH = 200
VOLUNTEER_ADDRESS_MAX_LENGTH = 200


class VolunteerBase(SQLModel):
    last_name: str = Field(max_length=VOLUNTEER_NAME_MAX_LENGTH, nullable=False)
    first_name: str = Field(max_length=VOLUNTEER_NAME_MAX_LENGTH, nullable=False)
    phone_number: str = Field(max_length=VOLUNTEER_PHONE_MAX_LENGTH, nullable=False)
    birthdate: date = Field(nullable=False)
    skills: str = Field(
        default="", max_length=VOLUNTEER_SKILLS_MAX_LENGTH, nullable=False
    )
    address: str | None = Field(default=None, max_length=VOLUNTEER_ADDRESS_MAX_LENGTH)
    zip_code: str | None = Field(default=None, max_length=VOLUNTEER_ZIP_MAX_LENGTH)
    bio: str = Field(default="", max_length=VOLUNTEER_BIO_MAX_LENGTH, nullable=False)


class Volunteer(VolunteerBase, table=True):
    id_volunteer: int | None = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="user.id_user", unique=True)
    user: "User" = Relationship(back_populates="volunteer_profile")
    badges: list["Badge"] = Relationship(back_populates="volunteers", link_model=Assign)
    missions: list["Mission"] = Relationship(
        back_populates="volunteers", link_model=Engagement
    )
    favorite_missions: list["Mission"] = Relationship(
        sa_relationship_kwargs={"secondary": "favorite", "lazy": "noload"}
    )


class VolunteerCreate(VolunteerBase):
    pass


class VolunteerPublic(VolunteerBase):
    id_volunteer: int
    id_user: int
    active_missions_count: int = 0
    finished_missions_count: int = 0
    user: UserPublic | None = None


class VolunteerUpdate(SQLModel):
    # Volunteer profile fields
    last_name: str | None = Field(default=None, max_length=VOLUNTEER_NAME_MAX_LENGTH)
    first_name: str | None = Field(default=None, max_length=VOLUNTEER_NAME_MAX_LENGTH)
    phone_number: str | None = Field(
        default=None, max_length=VOLUNTEER_PHONE_MAX_LENGTH
    )
    birthdate: date | None = None
    skills: str | None = Field(default=None, max_length=VOLUNTEER_SKILLS_MAX_LENGTH)
    address: str | None = Field(default=None, max_length=VOLUNTEER_ADDRESS_MAX_LENGTH)
    zip_code: str | None = Field(default=None, max_length=VOLUNTEER_ZIP_MAX_LENGTH)
    bio: str | None = Field(default=None, max_length=VOLUNTEER_BIO_MAX_LENGTH)
    # User account fields
    email: EmailStr | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH)
