from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from typing import Annotated

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str):
    return pwd_context.hash(password)


def decode_token(token):
    return


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = None  # TODO decode
    return user
