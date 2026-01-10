from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.mission_category import MissionCategory

if TYPE_CHECKING:
    from app.models.mission import Mission


class CategoryBase(SQLModel):
    label: str


class Category(CategoryBase, table=True):
    id_categ: int | None = Field(default=None, primary_key=True)
    missions: list["Mission"] = Relationship(
        back_populates="categories", link_model=MissionCategory
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryPublic(CategoryBase):
    id_categ: int


class CategoryUpdate(SQLModel):
    label: str | None = None
