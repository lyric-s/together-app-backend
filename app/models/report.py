from datetime import timezone
from datetime import datetime
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import ProcessingStatus, ReportType, ReportTarget

if TYPE_CHECKING:
    from app.models.user import User

# Validation constants
REASON_MIN_LENGTH = 10
REASON_MAX_LENGTH = 500


class ReportBase(SQLModel):
    type: ReportType = Field(description="Type of report")
    target: ReportTarget = Field(description="What is being reported")
    reason: str = Field(min_length=REASON_MIN_LENGTH, max_length=REASON_MAX_LENGTH)
    id_user_reported: int = Field(foreign_key="user.id_user")


class Report(ReportBase, table=True):
    id_report: int | None = Field(default=None, primary_key=True)
    id_user_reporter: int = Field(foreign_key="user.id_user")
    state: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    date_reporting: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reporter: "User" = Relationship(
        back_populates="reports_made",
        sa_relationship_kwargs={"foreign_keys": "[Report.id_user_reporter]"},
    )
    reported_user: "User" = Relationship(
        back_populates="reports_received",
        sa_relationship_kwargs={"foreign_keys": "[Report.id_user_reported]"},
    )


class ReportCreate(ReportBase):
    pass


class ReportPublic(ReportBase):
    id_report: int
    state: ProcessingStatus
    date_reporting: datetime


class ReportUpdate(SQLModel):
    state: ProcessingStatus | None = Field(
        default=None, description="Admin can update report state"
    )
