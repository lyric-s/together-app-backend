from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import EmailStr
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums import UserType

if TYPE_CHECKING:
    from app.models.volunteer import Volunteer
    from app.models.association import Association
    from app.models.report import Report

# Field constraints
USERNAME_MAX_LENGTH = 50
EMAIL_MAX_LENGTH = 255
PASSWORD_MIN_LENGTH = 8


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, max_length=USERNAME_MAX_LENGTH)
    email: EmailStr = Field(unique=True, index=True, max_length=EMAIL_MAX_LENGTH)
    user_type: UserType = Field(index=True)


class User(UserBase, table=True):
    id_user: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field(nullable=False)
    date_creation: datetime = Field(default_factory=datetime.now)
    hashed_refresh_token: str | None = Field(default=None, nullable=True)
    volunteer_profile: "Volunteer" = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    association_profile: "Association" = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    reports_made: list["Report"] = Relationship(
        back_populates="reporter",
        sa_relationship_kwargs={"foreign_keys": "[Report.id_user_reporter]"},
    )
    reports_received: list["Report"] = Relationship(
        back_populates="reported_user",
        sa_relationship_kwargs={"foreign_keys": "[Report.id_user_reported]"},
    )


class UserCreate(UserBase):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                    "user_type": "VOLUNTEER",
                    "password": "SecurePass123!",
                }
            ]
        }
    }


class UserPublic(UserBase):
    id_user: int
    date_creation: datetime


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    user_type: UserType | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH)
