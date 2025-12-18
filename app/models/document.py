from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import ProcessingStatus

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.association import Association


class DocumentBase(SQLModel, table=True):
    doc_name: str
    url_doc: str
    date_upload: datetime
    verif_state: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    id_admin: int | None = Field(default=None, foreign_key="admin.id_admin")
    id_asso: int = Field(foreign_key="association.id_asso")


class Document(DocumentBase):
    id_doc: int | None = Field(default=None, primary_key=True)
    admin: "Admin" = Relationship(back_populates="documents")
    association: "Association" = Relationship(back_populates="documents")


class DocumentCreate(DocumentBase):
    pass


class DocumentPublic(DocumentBase):
    id_doc: int


class DocumentUpdate(SQLModel):
    doc_name: str | None = None
    url_doc: str | None = None
