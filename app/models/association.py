from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User, UserCreate, UserUpdate, UserPublic
    from app.models.mission import Mission
    from app.models.document import Document


class AssociationBase(SQLModel):
    name: str = Field(index=True, max_length=50)
    address: str
    country: str = Field(max_length=50)
    zip_code: str = Field(max_length=50)
    rna_code: str = Field(max_length=50)
    company_name: str
    description: str


class Association(AssociationBase, table=True):
    id_asso: int | None = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="user.id_user")
    user: "User" = Relationship(back_populates="association_profile")
    missions: list["Mission"] = Relationship(back_populates="association")
    documents: list["Document"] = Relationship(back_populates="association")


class AssociationCreate(AssociationBase):
    user: "UserCreate"


class AssociationPublic(AssociationBase):
    id_asso: int
    id_user: int
    user: "UserPublic"


class AssociationUpdate(SQLModel):
    user: "UserUpdate"
    name: str | None = None
    address: str | None = None
    country: str | None = None
    zip_code: str | None = None
    rna_code: str | None = None
    company_name: str | None = None
    description: str | None = None
