from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user_type: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1Ni...",
                    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                    "token_type": "bearer",
                    "user_type": "volunteer",
                },
                {
                    "access_token": "eyJhbGciOiJIUzI1Ni...",
                    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                    "token_type": "bearer",
                    "user_type": "association",
                },
                {
                    "access_token": "eyJhbGciOiJIUzI1Ni...",
                    "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
                    "token_type": "bearer",
                    "user_type": "admin",
                },
            ]
        }
    }


class TokenData(BaseModel):
    username: str | None = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsInR5cGUiOiJyZWZyZXNoIiwiZXhwIjoxNzM4ODg4ODg4fQ.example_signature"
                }
            ]
        }
    }
