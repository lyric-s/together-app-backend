"""Notification models for association activity feed."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, ForeignKey
from enum import Enum

if TYPE_CHECKING:
    from app.models.association import Association
    from app.models.mission import Mission
    from app.models.user import User


class NotificationType(str, Enum):
    """Types of notifications for associations."""

    VOLUNTEER_JOINED = "volunteer_joined"
    VOLUNTEER_LEFT = "volunteer_left"
    VOLUNTEER_WITHDREW = "volunteer_withdrew"
    CAPACITY_REACHED = "capacity_reached"
    MISSION_DELETED = "mission_deleted"


class NotificationBase(SQLModel):
    """Base notification fields."""

    notification_type: NotificationType
    message: str = Field(max_length=500)
    related_mission_id: int | None = Field(default=None)
    related_user_id: int | None = Field(default=None)
    is_read: bool = Field(default=False)


class Notification(NotificationBase, table=True):
    """Database notification model."""

    id_notification: int | None = Field(default=None, primary_key=True)
    id_asso: int = Field(
        sa_column=Column(
            ForeignKey(
                "association.id_asso",
                ondelete="CASCADE",
                name="notification_id_asso_fkey",
            ),
            nullable=False,
            index=True,
        )
    )
    related_mission_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey(
                "mission.id_mission",
                ondelete="CASCADE",
                name="notification_related_mission_id_fkey",
            ),
            nullable=True,
        ),
    )
    related_user_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey(
                "user.id_user",
                ondelete="SET NULL",
                name="notification_related_user_id_fkey",
            ),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )

    # Relationships
    association: "Association" = Relationship(back_populates="notifications")
    mission: Optional["Mission"] = Relationship()
    related_user: Optional["User"] = Relationship()


class NotificationPublic(NotificationBase):
    """Public notification response."""

    id_notification: int
    created_at: datetime


class NotificationCreate(SQLModel):
    """Schema for creating notifications (internal use)."""

    id_asso: int
    notification_type: NotificationType
    message: str = Field(max_length=500)
    related_mission_id: int | None = None
    related_user_id: int | None = None


class NotificationMarkRead(SQLModel):
    """Schema for marking notifications as read."""

    notification_ids: list[int] = Field(min_items=1)


class BulkEmailRequest(SQLModel):
    """Schema for sending bulk emails to mission volunteers."""

    mission_id: int
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
