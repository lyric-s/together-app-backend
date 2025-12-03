# from typing import Annotated
# from fastapi import APIRouter, Depends

# from app.dependencies import get_current_active_user
# from app.models.user import User


# router = APIRouter(prefix="/user", tags=["user"])


# @router.get("/users/me/", response_model=User)
# async def read_users_me(
#     current_user: Annotated[User, Depends(get_current_active_user)],
# ):
#     return current_user


# @router.get("/users/me/items/")
# async def read_own_items(
#     current_user: Annotated[User, Depends(get_current_active_user)],
# ):
#     return [{"item_id": "Foo", "owner": current_user.username}]
