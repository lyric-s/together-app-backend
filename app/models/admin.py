from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.document import Document


class AdminBase(SQLModel):
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field(index=True)
    username: str = Field(unique=True, index=True)


class Admin(AdminBase, table=True):
    id_admin: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    documents: list["Document"] = Relationship(back_populates="admin")


class AdminCreate(AdminBase):
    password: str


class AdminPublic(AdminBase):
    id_admin: int


class AdminUpdate(SQLModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
