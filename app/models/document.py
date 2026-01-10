from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import ProcessingStatus

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.association import Association


class DocumentBase(SQLModel):
    doc_name: str
    url_doc: str
    date_upload: datetime = Field(default_factory=datetime.now)
    verif_state: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    id_admin: int | None = Field(
        default=None, foreign_key="admin.id_admin", nullable=True
    )
    id_asso: int = Field(foreign_key="association.id_asso")


class Document(DocumentBase, table=True):
    id_doc: int | None = Field(default=None, primary_key=True)
    admin: "Admin" = Relationship(back_populates="documents")
    association: "Association" = Relationship(back_populates="documents")


class DocumentCreate(DocumentBase):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doc_name": "Association RNA Certificate",
                    "url_doc": "https://storage.together-app.fr/documents/rna-cert-w751234567.pdf",
                    "date_upload": "2025-01-15T10:30:00",
                    "verif_state": "PENDING",
                    "id_admin": None,
                    "id_asso": 5,
                }
            ]
        }
    }


class DocumentPublic(DocumentBase):
    id_doc: int


class DocumentUpdate(SQLModel):
    doc_name: str | None = None
    url_doc: str | None = None
    verif_state: ProcessingStatus | None = None
    id_admin: int | None = None

    model_config = {
        "json_schema_extra": {"examples": [{"verif_state": "APPROVED", "id_admin": 3}]}
    }
