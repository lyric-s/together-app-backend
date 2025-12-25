from app.database.database import create_db_and_tables
from pathlib import Path
from app.utils.logger import setup_logging
from contextlib import asynccontextmanager
from app.core.config import get_settings, parse_comma_separated_origins
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.internal import admin
from app.routers import auth
from app.core.telemetry import setup_telemetry

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Perform application startup tasks before the FastAPI app begins serving requests.

    Runs logging setup, creates the database and tables, and initializes telemetry using the provided FastAPI application. This function is intended to be used as an async lifespan context manager and yields control after startup actions complete.
    """
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
    allow_origins=[
        str(origin)
        for origin in parse_comma_separated_origins(get_settings().BACKEND_CORS_ORIGINS)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serve the application's favicon file.

    Returns:
        FileResponse: The `favicon.ico` file served from the project's base directory (`BASE_DIR / "favicon.ico"`).
    """
    return FileResponse(BASE_DIR / "favicon.ico")


@app.get("/health", include_in_schema=False)
def health_check():
    """
    Provide the application's liveness state for health checks.

    Returns:
        dict: A mapping with key "status" and value "ok" indicating the service is healthy.
    """
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(admin.router)
