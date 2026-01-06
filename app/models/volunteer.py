from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship
from app.models.assign import Assign
from app.models.engagement import Engagement

if TYPE_CHECKING:
    from app.models.user import User, UserPublic
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
    active_missions_count: int = Field(default=0)
    finished_missions_count: int = Field(default=0)
    user: "User" = Relationship(back_populates="volunteer_profile")
    badges: list["Badge"] = Relationship(back_populates="volunteers", link_model=Assign)
    missions: list["Mission"] = Relationship(
        back_populates="volunteers", link_model=Engagement
    )


class VolunteerCreate(VolunteerBase):
    # TODO (Create User first via Auth, then create volunteer profile linked to it ?)
    pass


class VolunteerPublic(VolunteerBase):
    id_volunteer: int
    id_user: int
    active_missions_count: int
    finished_missions_count: int
    user: Optional["UserPublic"] = None


class VolunteerUpdate(SQLModel):
    # TODO find a way to update User related attributes
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
    # Note: active_missions_count and finished_missions_count are
    # computed fields and should not be updated directly
