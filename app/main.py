from app.database.database import create_db_and_tables
from pathlib import Path
from app.utils.logger import setup_logging
from contextlib import asynccontextmanager
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.internal import admin
from app.routers import auth
from app.core.telemetry import setup_telemetry

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    create_db_and_tables()
    setup_telemetry(app)
    yield


app = FastAPI(
    title="Together API",
    description="RESTful API for the Together application",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in get_settings().BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(BASE_DIR / "favicon.ico")


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(admin.router)
