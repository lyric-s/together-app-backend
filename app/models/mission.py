from datetime import date
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.engagement import Engagement

if TYPE_CHECKING:
    from app.models.association import Association
    from app.models.location import Location
    from app.models.category import Category
    from app.models.volunteer import Volunteer


class MissionBase(SQLModel):
    name: str = Field(max_length=50)
    id_location: int = Field(foreign_key="location.id_location")
    id_categ: int = Field(foreign_key="category.id_categ")
    id_asso: int = Field(foreign_key="association.id_asso")
    date_start: date
    date_end: date
    skills: str = Field(max_length=50)
    description: str = Field(max_length=3000)
    capacity_min: int
    capacity_max: int
    image_url: str | None = None


class Mission(MissionBase, table=True):
    id_mission: int | None = Field(default=None, primary_key=True)
    location: "Location" = Relationship(back_populates="missions")
    category: "Category" = Relationship(back_populates="missions")
    association: "Association" = Relationship(back_populates="missions")
    volunteers: list["Volunteer"] = Relationship(
        back_populates="missions", link_model=Engagement
    )


class MissionCreate(MissionBase):
    pass


class MissionPublic(MissionBase):
    id_mission: int


class MissionUpdate(SQLModel):
    id_location: int | None = None
    id_categ: int | None = None
    id_asso: int | None = None
    name: str | None = Field(default=None, max_length=50)
    date_start: date | None = None
    date_end: date | None = None
    skills: str | None = Field(default=None, max_length=50)
    description: str | None = None
    capacity_min: int | None = None
    capacity_max: int | None = None
    image_url: str | None = None
