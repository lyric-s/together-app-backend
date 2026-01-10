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
    image_url: str | None = Field(default=None, nullable=True)


class Mission(MissionBase, table=True):
    id_mission: int | None = Field(default=None, primary_key=True)
    location: "Location" = Relationship(back_populates="missions")
    category: "Category" = Relationship(back_populates="missions")
    association: "Association" = Relationship(back_populates="missions")
    volunteers: list["Volunteer"] = Relationship(
        back_populates="missions", link_model=Engagement
    )


class MissionCreate(MissionBase):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Community Food Distribution",
                    "id_location": 1,
                    "id_categ": 2,
                    "id_asso": 5,
                    "date_start": "2026-02-15",
                    "date_end": "2026-02-15",
                    "skills": "Organization, communication, physical work",
                    "description": "Help distribute food packages to families in need. We need volunteers to assist with organizing, packing, and distributing food items. This is a one-day event that will make a real difference in our community.",
                    "capacity_min": 5,
                    "capacity_max": 15,
                    "image_url": "https://example.com/images/food-distribution.jpg",
                }
            ]
        }
    }


class MissionPublic(MissionBase):
    id_mission: int


class MissionUpdate(SQLModel):
    id_location: int | None = None
    id_categ: int | None = None
    name: str | None = Field(default=None, max_length=50)
    date_start: date | None = None
    date_end: date | None = None
    skills: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=3000)
    capacity_min: int | None = None
    capacity_max: int | None = None
    image_url: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "capacity_max": 20,
                    "description": "Updated description: Help distribute food packages to families in need. We've increased capacity due to high demand.",
                    "image_url": "https://example.com/images/food-distribution-updated.jpg",
                }
            ]
        }
    }
