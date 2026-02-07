from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.enums import (
    ProcessingStatus,
    ReportTarget,
    AIContentCategory,
)


class AIReport(SQLModel, table=True):
    """
    Represents a report generated automatically by the AI content moderation system.

    This model stores the results of an AI-based analysis of user-generated content
    (e.g., user profiles, missions) that has been flagged as potentially non-compliant.
    """

    id_report: Optional[int] = Field(default=None, primary_key=True)

    # -- Target Information --
    target: ReportTarget = Field(
        description="The type of content that was flagged (e.g., PROFILE or MISSION)."
    )
    target_id: int = Field(
        description="The ID of the content that was flagged (e.g., user_id or mission_id)."
    )

    # -- AI Analysis Results --
    classification: AIContentCategory = Field(
        description="The classification label returned by the AI model (e.g., 'NORMAL_CONTENT', 'FRAUD_SUSPECTED')."
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="The confidence score (0.0 to 1.0) associated with the classification, if provided.",
    )
    model_version: str = Field(
        description="The version of the AI model that performed the analysis."
    )

    # -- Moderation Workflow --
    state: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING,
        description="The current status of the moderation review (e.g., PENDING, APPROVED, REJECTED).",
    )

    # -- Timestamps --
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="The timestamp when the AI report was created.",
    )


class AIReportPublic(SQLModel):
    id_report: int
    target: ReportTarget
    target_id: int
    classification: AIContentCategory
    confidence_score: Optional[float] = None
    model_version: str
    state: ProcessingStatus
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id_report": 1,
                    "target": "PROFILE",
                    "target_id": 42,
                    "classification": "SPAM_LIKE",
                    "confidence_score": 0.95,
                    "model_version": "CamemBERT-MultiModel-v1.0",
                    "state": "PENDING",
                    "created_at": "2026-01-29T10:00:00Z",
                }
            ]
        }
    }


class AIReportUpdate(SQLModel):
    state: ProcessingStatus = Field(
        description="The new status of the AI report (APPROVED/REJECTED)."
    )
