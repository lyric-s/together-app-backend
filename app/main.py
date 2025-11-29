from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.internal import admin
from app.routers import user, auth

app = FastAPI(
    title="Together API",
    description="RESTful API for the Together web application",
)

# Set all CORS enabled origins
# if get_settings().all_cors_origins:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=get_settings.all_cors_origins,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )


app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(user.router)

# from datetime import timedelta
# from typing import Annotated

# from fastapi import Depends, HTTPException, status, APIRouter
# from fastapi.security import OAuth2PasswordRequestForm

# from app.core.config import get_settings
# from app.core.security import authenticate_user, create_access_token
# from app.dependencies import get_db
# from app.models.token import Token

# router = APIRouter(prefix="/auth", tags=["auth"])


# @app.post("/token")
# async def login_for_access_token(
#     form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
# ) -> Token:
#     user = authenticate_user(get_db(), form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
#     access_token = create_access_token(
#         data={"sub": user.username}, expires_delta=access_token_expires
#     )
#     return Token(access_token=access_token, token_type="bearer")
