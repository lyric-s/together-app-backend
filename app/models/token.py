from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str
