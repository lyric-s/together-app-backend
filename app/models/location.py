from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.mission import Mission


class LocationBase(SQLModel):
    address: str | None = None
    country: str | None = Field(default=None, max_length=50)
    zip_code: str | None = Field(default=None, max_length=50)
    lat: float | None = None
    longitude: float | None = Field(default=None, alias="long")


class Location(LocationBase, table=True):
    id_location: int | None = Field(default=None, primary_key=True)
    missions: list["Mission"] = Relationship(back_populates="location")


class LocationCreate(LocationBase):
    pass


class LocationPublic(LocationBase):
    pass


class LocationUpdate(SQLModel):
    address: str | None = None
    country: str | None = Field(default=None, max_length=50)
    zip_code: str | None = Field(default=None, max_length=50)
    lat: float | None = None
    longitude: float | None = Field(default=None, alias="long")
