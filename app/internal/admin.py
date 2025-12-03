from fastapi import APIRouter, Depends
from app.dependencies import validate_current_user

router = APIRouter(
    prefix="/admin", tags=["internal"], dependencies=[Depends(validate_current_user)]
)


@router.get("/admins/")
def get_admins():
    return {"admins": ""}
