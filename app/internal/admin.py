from fastapi import APIRouter, Depends
from app.dependencies import validate_current_user
from app.core.config import settings

router = APIRouter(
    prefix="/admin", tags=["internal"], dependencies=[Depends(validate_current_user)]
)


@router.get("/settings/")
def get_admins():
    return {"Current settings": settings.model_dump()}
