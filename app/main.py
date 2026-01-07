from pathlib import Path
from app.utils.logger import setup_logging
from contextlib import asynccontextmanager
from app.core.config import get_settings, parse_comma_separated_origins
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.internal import admin
from app.routers import auth, volunteer
from app.core.telemetry import setup_telemetry
from app.services.storage import storage_service
from app.core.error_handlers import register_exception_handlers

BASE_DIR = Path(__file__).resolve().parent.parent
# Ensure static directory exists before later mount
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Run startup tasks required before the application begins serving requests.

    Initializes logging and telemetry, and ensures the storage bucket exists. Intended to be used as an async lifespan context manager for a FastAPI application; yields control after startup tasks complete.

    Parameters:
        app (FastAPI): The FastAPI application instance used for telemetry initialization.
    """
    setup_logging()
    setup_telemetry(app)
    storage_service.ensure_bucket_exists()
    yield


app = FastAPI(
    title="Together API",
    description="RESTful API for the Together application",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

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
app.include_router(admin.router)
