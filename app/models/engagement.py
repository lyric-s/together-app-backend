from datetime import date
from sqlmodel import SQLModel, Field
from .enums import ProcessingStatus


class Engagement(SQLModel, table=True):
    id_volunteer: int = Field(foreign_key="volunteer.id_volunteer", primary_key=True)
    id_mission: int = Field(foreign_key="mission.id_mission", primary_key=True)
    state: ProcessingStatus | None = None
    message: str | None = None
    application_date: date | None = Field(default_factory=date.today)
    rejection_reason: str | None = None
