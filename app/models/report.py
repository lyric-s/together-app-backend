from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import ProcessingStatus

if TYPE_CHECKING:
    from app.models.user import User


class ReportBase(SQLModel, table=True):
    type: str | None = Field(default=None, max_length=50)
    target: str | None = Field(default=None, max_length=50)
    reason: str
    id_user_reporter: int = Field(foreign_key="user.id_user")
    id_user_reported: int = Field(foreign_key="user.id_user")


class Report(ReportBase):
    id_report: int | None = Field(default=None, primary_key=True)
    state: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    date_reporting: datetime = Field(default_factory=datetime.now)
    reporter: "User" = Relationship(
        back_populates="reports_made",
        sa_relationship_kwargs={"foreign_keys": "[Reports.id_user_reporter]"},
    )
    reported_user: "User" = Relationship(
        back_populates="reports_received",
        sa_relationship_kwargs={"foreign_keys": "[Reports.id_user_reported]"},
    )


class ReportCreate(ReportBase):
    pass


class ReportPublic(ReportBase):
    id_report: int
    state: ProcessingStatus
    date_reporting: datetime


class ReportUpdate(SQLModel):
    type: str | None = None
    target: str | None = None
    reason: str | None = None
    state: ProcessingStatus | None = None
    id_user_reporter: int | None = None
    id_user_reported: int | None = None
