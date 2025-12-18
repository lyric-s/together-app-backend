from datetime import date
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.assign import Assign
from app.models.engagement import Engagement

if TYPE_CHECKING:
    from app.models.user import User, UserPublic, UserUpdate
    from app.models.badge import Badge
    from app.models.mission import Mission


class VolunteerBase(SQLModel):
    last_name: str = Field(max_length=50)
    first_name: str = Field(max_length=50)
    phone_number: str = Field(max_length=50)
    birthdate: date
    skills: str = Field(max_length=500)
    address: str | None = Field(default=None)
    zip_code: str | None = Field(default=None, max_length=50)
    bio: str = Field(default="", max_length=200)


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
    # TODO (Create User first via Auth, then create voluntree profile linked to it)
    pass


class VolunteerPublic(VolunteerBase):
    id_volunteer: int
    id_user: int
    active_missions_count: int
    finished_missions_count: int
    user: "UserPublic" | None = None


class VolunteerUpdate(SQLModel):
    user: "UserUpdate" | None = None
    last_name: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, max_length=50)
    phone_number: str | None = Field(default=None, max_length=50)
    birthdate: date | None = None
    skills: str | None = Field(default=None, max_length=500)
    address: str | None = None
    zip_code: str | None = Field(default=None, max_length=50)
    bio: str | None = Field(default=None, max_length=200)
    # active_missions_count and finished_missions_count should
    # be handled in the database
