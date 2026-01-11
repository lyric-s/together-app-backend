from datetime import date
from sqlmodel import SQLModel, Field
from .enums import ProcessingStatus


class Engagement(SQLModel, table=True):
    id_volunteer: int = Field(foreign_key="volunteer.id_volunteer", primary_key=True)
    id_mission: int = Field(foreign_key="mission.id_mission", primary_key=True)
    state: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    message: str | None = Field(default=None, max_length=1000, nullable=True)
    application_date: date = Field(default_factory=date.today)
    rejection_reason: str | None = Field(default=None, max_length=500, nullable=True)


class RejectEngagementRequest(SQLModel):
    rejection_reason: str = Field(min_length=1, max_length=500)


class EngagementPublic(SQLModel):
    id_volunteer: int
    id_mission: int
    state: ProcessingStatus
    message: str | None
    application_date: date
    rejection_reason: str | None
