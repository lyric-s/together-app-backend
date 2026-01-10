"""Password reset request and response models."""

from pydantic import EmailStr
from sqlmodel import SQLModel, Field


class PasswordResetRequest(SQLModel):
    """Request model for initiating password reset."""

    email: EmailStr


class PasswordResetConfirm(SQLModel):
    """Request model for confirming password reset with token."""

    token: str = Field(min_length=64, max_length=64)
    new_password: str = Field(min_length=8)


class PasswordResetResponse(SQLModel):
    """Response model for password reset operations."""

    message: str
