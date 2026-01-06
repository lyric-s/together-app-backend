from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.document import Document

# Field constraints
ADMIN_NAME_MAX_LENGTH = 50
ADMIN_USERNAME_MAX_LENGTH = 50
ADMIN_EMAIL_MAX_LENGTH = 255
ADMIN_PASSWORD_MIN_LENGTH = 8


class AdminBase(SQLModel):
    first_name: str = Field(max_length=ADMIN_NAME_MAX_LENGTH, nullable=False)
    last_name: str = Field(max_length=ADMIN_NAME_MAX_LENGTH, nullable=False)
    email: str = Field(max_length=ADMIN_EMAIL_MAX_LENGTH, index=True, nullable=False)
    username: str = Field(
        max_length=ADMIN_USERNAME_MAX_LENGTH, unique=True, index=True, nullable=False
    )


class Admin(AdminBase, table=True):
    id_admin: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field(nullable=False)
    documents: list["Document"] = Relationship(back_populates="admin")


class AdminCreate(AdminBase):
    password: str = Field(min_length=ADMIN_PASSWORD_MIN_LENGTH)


class AdminPublic(AdminBase):
    id_admin: int


class AdminUpdate(SQLModel):
    first_name: str | None = Field(default=None, max_length=ADMIN_NAME_MAX_LENGTH)
    last_name: str | None = Field(default=None, max_length=ADMIN_NAME_MAX_LENGTH)
    email: str | None = Field(default=None, max_length=ADMIN_EMAIL_MAX_LENGTH)
    password: str | None = Field(default=None, min_length=ADMIN_PASSWORD_MIN_LENGTH)
