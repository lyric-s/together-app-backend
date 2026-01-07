from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.mission import Mission


class LocationBase(SQLModel):
    address: str | None = Field(default=None, max_length=255, nullable=True)
    country: str | None = Field(default=None, max_length=50, nullable=True)
    zip_code: str | None = Field(default=None, max_length=50, nullable=True)
    lat: float | None = Field(default=None, ge=-90, le=90, nullable=True)
    longitude: float | None = Field(
        default=None, alias="long", ge=-180, le=180, nullable=True
    )


class Location(LocationBase, table=True):
    id_location: int | None = Field(default=None, primary_key=True)
    missions: list["Mission"] = Relationship(back_populates="location")


class LocationCreate(LocationBase):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "address": "15 Rue de la Paix",
                    "country": "France",
                    "zip_code": "75002",
                    "lat": 48.8698,
                    "long": 2.3314,
                }
            ]
        }
    }


class LocationPublic(LocationBase):
    id_location: int


class LocationUpdate(SQLModel):
    address: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=50)
    zip_code: str | None = Field(default=None, max_length=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, alias="long", ge=-180, le=180)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"address": "28 Avenue des Champs-Élysées", "zip_code": "75008"}
            ]
        }
    }
