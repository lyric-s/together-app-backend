from datetime import date
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.engagement import Engagement
from app.models.mission_category import MissionCategory

if TYPE_CHECKING:
    from app.models.association import Association, AssociationPublic
    from app.models.location import Location, LocationPublic
    from app.models.category import Category, CategoryPublic
    from app.models.volunteer import Volunteer


class MissionBase(SQLModel):
    name: str = Field(max_length=50)
    id_location: int = Field(foreign_key="location.id_location")
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
    categories: list["Category"] = Relationship(
        back_populates="missions", link_model=MissionCategory
    )
    association: "Association" = Relationship(back_populates="missions")
    volunteers: list["Volunteer"] = Relationship(
        back_populates="missions", link_model=Engagement
    )


class MissionCreate(MissionBase):
    category_ids: list[int] = Field(min_length=1, max_length=5)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Community Food Distribution",
                    "id_location": 1,
                    "category_ids": [1, 10],
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

    # Embedded relationships
    location: "LocationPublic | None" = None
    categories: list["CategoryPublic"] = []
    association: "AssociationPublic | None" = None

    # Computed capacity fields
    volunteers_enrolled: int = 0
    available_slots: int = 0
    is_full: bool = False


class MissionUpdate(SQLModel):
    id_location: int | None = None
    category_ids: list[int] | None = Field(default=None, min_length=1, max_length=5)
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
                    "category_ids": [1, 10, 15],
                    "description": "Updated description: Help distribute food packages to families in need. We've increased capacity due to high demand.",
                    "image_url": "https://example.com/images/food-distribution-updated.jpg",
                }
            ]
        }
    }


# Rebuild MissionPublic after all referenced models are available
from app.models.location import LocationPublic  # noqa: E402
from app.models.category import CategoryPublic  # noqa: E402
from app.models.association import AssociationPublic  # noqa: E402

MissionPublic.model_rebuild()
