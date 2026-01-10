"""Mission-Category junction table for many-to-many relationship."""

from sqlmodel import SQLModel, Field


class MissionCategory(SQLModel, table=True):
    """
    Junction table linking missions to categories.

    Enables many-to-many relationship where:
    - A mission can have multiple categories
    - A category can be assigned to multiple missions

    Composite primary key ensures each mission-category pair is unique.
    """

    id_mission: int = Field(foreign_key="mission.id_mission", primary_key=True)
    id_categ: int = Field(foreign_key="category.id_categ", primary_key=True)
