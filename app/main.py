from fastapi import FastAPI
from app.internal import admin

app = FastAPI(
    title="Together API",
    description="RESTful API for the Together web application",
)

app.include_router(admin.router)
