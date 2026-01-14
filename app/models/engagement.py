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


class EngagementWithVolunteer(SQLModel):
    """Engagement with volunteer details for association dashboard."""

    id_volunteer: int
    id_mission: int
    state: ProcessingStatus
    message: str | None
    application_date: date
    rejection_reason: str | None
    # Volunteer details
    volunteer_first_name: str
    volunteer_last_name: str
    volunteer_email: str
    volunteer_phone: str
    volunteer_skills: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id_volunteer": 42,
                    "id_mission": 15,
                    "state": "PENDING",
                    "message": "I have experience with food bank volunteering and would love to help.",
                    "application_date": "2026-01-14",
                    "rejection_reason": None,
                    "volunteer_first_name": "Sarah",
                    "volunteer_last_name": "Johnson",
                    "volunteer_email": "sarah@example.com",
                    "volunteer_phone": "+33612345678",
                    "volunteer_skills": "First aid certified, Fluent in English and French",
                }
            ]
        }
    }
