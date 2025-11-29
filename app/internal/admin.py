from fastapi import APIRouter, Depends
from typing import Annotated
from app.dependencies import oauth2_scheme

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/admins/")
def get_admins(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
