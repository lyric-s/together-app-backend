from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User, UserPublic
    from app.models.mission import Mission
    from app.models.document import Document

# Field constraints
ASSOCIATION_NAME_MAX_LENGTH = 50
ASSOCIATION_ADDRESS_MAX_LENGTH = 200
ASSOCIATION_COUNTRY_MAX_LENGTH = 50
ASSOCIATION_ZIP_MAX_LENGTH = 10
ASSOCIATION_RNA_CODE_MAX_LENGTH = 50
ASSOCIATION_COMPANY_NAME_MAX_LENGTH = 200
ASSOCIATION_DESCRIPTION_MAX_LENGTH = 1000


class AssociationBase(SQLModel):
    name: str = Field(max_length=ASSOCIATION_NAME_MAX_LENGTH, nullable=False)
    address: str = Field(max_length=ASSOCIATION_ADDRESS_MAX_LENGTH, nullable=False)
    country: str = Field(max_length=ASSOCIATION_COUNTRY_MAX_LENGTH, nullable=False)
    zip_code: str = Field(max_length=ASSOCIATION_ZIP_MAX_LENGTH, nullable=False)
    rna_code: str = Field(
        index=True, max_length=ASSOCIATION_RNA_CODE_MAX_LENGTH, nullable=False
    )
    company_name: str = Field(
        max_length=ASSOCIATION_COMPANY_NAME_MAX_LENGTH, nullable=False
    )
    description: str = Field(
        default="", max_length=ASSOCIATION_DESCRIPTION_MAX_LENGTH, nullable=False
    )


class Association(AssociationBase, table=True):
    id_asso: int | None = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="user.id_user", unique=True)
    user: "User" = Relationship(back_populates="association_profile")
    missions: list["Mission"] = Relationship(back_populates="association")
    documents: list["Document"] = Relationship(back_populates="association")


class AssociationCreate(AssociationBase):
    pass


class AssociationPublic(AssociationBase):
    id_asso: int
    id_user: int
    # TODO use .options(selectinload(Association.user)) in the query
    user: Optional["UserPublic"] = None


class AssociationUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=ASSOCIATION_NAME_MAX_LENGTH)
    address: str | None = Field(default=None, max_length=ASSOCIATION_ADDRESS_MAX_LENGTH)
    country: str | None = Field(default=None, max_length=ASSOCIATION_COUNTRY_MAX_LENGTH)
    zip_code: str | None = Field(default=None, max_length=ASSOCIATION_ZIP_MAX_LENGTH)
    rna_code: str | None = Field(
        default=None, max_length=ASSOCIATION_RNA_CODE_MAX_LENGTH
    )
    company_name: str | None = Field(
        default=None, max_length=ASSOCIATION_COMPANY_NAME_MAX_LENGTH
    )
    description: str | None = Field(
        default=None, max_length=ASSOCIATION_DESCRIPTION_MAX_LENGTH
    )
