from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.assign import Assign

if TYPE_CHECKING:
    from app.models.volunteer import Volunteer


class BadgeBase(SQLModel):
    title: str = Field(max_length=50, unique=True, index=True)
    condition: int
    reward: str = Field(max_length=50)


class Badge(BadgeBase, table=True):
    id_badge: int | None = Field(default=None, primary_key=True)
    volunteers: list["Volunteer"] = Relationship(
        back_populates="badges", link_model=Assign
    )


class BadgeCreate(BadgeBase):
    pass


class BadgePublic(BadgeBase):
    id_badge: int


class BadgeUpdate(SQLModel):
    title: str | None
    condition: int | None
    reward: str | None
