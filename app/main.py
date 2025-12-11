from app.utils.logger import setup_logging
from contextlib import asynccontextmanager
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.internal import admin
from app.routers import auth
from app.core.telemetry import setup_telemetry
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("System initialized with Loguru & OTel")
    yield


app = FastAPI(
    title="Together API",
    description="RESTful API for the Together web application",
    lifespan=lifespan,
)

setup_telemetry(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("favicon.ico")


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(admin.router)
app.include_router(auth.router)
