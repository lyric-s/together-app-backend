# from app.database.database import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import User, UserInDB
from typing import Annotated
from app.models.token import TokenData
import jwt
from jwt.exceptions import InvalidTokenError
from app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_db():
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    fake_users_db = {
        "johndoe": {
            "username": "johndoe",
            "full_name": "John Doe",
            "email": "johndoe@example.com",
            "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc",
            "disabled": False,
        }
    }
    return fake_users_db


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, get_settings().secret_key, algorithms=[get_settings().algorithm]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(get_db(), username=str(token_data.username))
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#     user = decode_token(token)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Not authenticated",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return user
