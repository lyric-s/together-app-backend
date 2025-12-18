from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.mission import Mission


class CategoryBase(SQLModel, table=True):
    label: str


class Category(CategoryBase, table=True):
    id_categ: int | None = Field(default=None, primary_key=True)
    label: str
    missions: list["Mission"] = Relationship(back_populates="category")


class CategoryCreate(CategoryBase):
    label: str


class CategoryPublic(CategoryBase):
    id_categ: int
