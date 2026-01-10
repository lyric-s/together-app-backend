"""Favorite model - link table for volunteer mission favorites."""

from datetime import datetime
from sqlmodel import SQLModel, Field


class Favorite(SQLModel, table=True):
    """Link table for volunteer-mission favorites (many-to-many)."""

    id_volunteer: int = Field(foreign_key="volunteer.id_volunteer", primary_key=True)
    id_mission: int = Field(foreign_key="mission.id_mission", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
