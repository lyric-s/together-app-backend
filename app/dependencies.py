from pydantic_settings import BaseSettings, SettingsConfigDict
from app.database.database import SessionLocal

class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()