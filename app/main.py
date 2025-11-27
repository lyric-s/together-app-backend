from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.internal import admin

app = FastAPI(
    title="Together API",
    description="RESTful API for the Together web application",
)

favicon_path = 'favicon.ico'

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)

app.include_router(admin.router)