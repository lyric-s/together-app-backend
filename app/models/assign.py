from sqlmodel import SQLModel, Field


class Assign(SQLModel, table=True):
    id_volunteer: int = Field(foreign_key="volunteer.id_volunteer", primary_key=True)
    id_badge: int = Field(foreign_key="badge.id_badge", primary_key=True)
