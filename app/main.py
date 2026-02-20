from pathlib import Path
import tomllib
from app.utils.logger import setup_logging
from contextlib import asynccontextmanager
from app.core.config import get_settings, parse_comma_separated_origins
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.internal import admin
from app.routers import (
    auth,
    volunteer,
    report,
    association,
    document,
    mission,
    category,
    ai_report,  # New AI report router
)
from app.core.telemetry import setup_telemetry
from app.services.storage import storage_service
from app.core.error_handlers import register_exception_handlers
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter
from app.core.ai_loader import load_models

BASE_DIR = Path(__file__).resolve().parent.parent
# Ensure static directory exists before later mount
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)


def get_project_version() -> str:
    """Read version from pyproject.toml."""
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "0.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Run startup tasks required before the application begins serving requests.

    Initializes logging, telemetry, ensures the storage bucket exists, and loads AI models.
    """
    setup_logging()
    setup_telemetry(app)
    storage_service.ensure_bucket_exists()
    load_models()  # Load AI models into memory
    yield


def get_api_description() -> str:
    """Read API description from markdown file."""
    try:
        with open("app/DESCRIPTION.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Together API"


app = FastAPI(
    title="Together API",
    version=get_project_version(),
    description=get_api_description(),
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Register exception handlers
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_comma_separated_origins(get_settings().BACKEND_CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounting the 'static' folder to serve generic assets
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static"), html=False),
    name="static",
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serve the application's favicon file.

    Returns:
        FileResponse: The `favicon.ico` file served from the project's base directory (`BASE_DIR / "favicon.ico"`).
    """
    return FileResponse(BASE_DIR / "static/favicon.ico")


@app.get("/health", include_in_schema=False)
def health_check():
    """
    Provide the application's liveness state for health checks.

    Returns:
        dict: A mapping with key "status" and value "ok" indicating the service is healthy.
    """
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(volunteer.router)
app.include_router(association.router)
app.include_router(document.router)
app.include_router(mission.router)
app.include_router(category.router)
app.include_router(report.router)
app.include_router(admin.router)
app.include_router(ai_report.router)  # Include the new AI Report router
