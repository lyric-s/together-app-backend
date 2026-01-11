"""Tests for auth router."""

from unittest.mock import patch, AsyncMock
from sqlmodel import Session
from fastapi.testclient import TestClient
from app.models.user import UserCreate
from app.models.enums import UserType
from app.services import user as user_service


class TestLogin:
    def test_login_user_success(self, session: Session, client: TestClient):
        # Create user
        user_in = UserCreate(
            username="login_user",
            email="login@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user_service.create_user(session, user_in)

        response = client.post(
            "/auth/token", data={"username": "login_user", "password": "Password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_type"] == "volunteer"

    def test_login_invalid_credentials(self, client: TestClient):
        response = client.post(
            "/auth/token", data={"username": "wrong", "password": "wrong"}
        )
        assert response.status_code == 401


class TestRefreshToken:
    def test_refresh_token_success(self, session: Session, client: TestClient):
        # Create user
        user_in = UserCreate(
            username="refresh_user",
            email="refresh@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        _ = user_service.create_user(session, user_in)

        # Login to get refresh token
        login_res = client.post(
            "/auth/token", data={"username": "refresh_user", "password": "Password123"}
        )
        refresh_token = login_res.json()["refresh_token"]

        # Refresh
        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != refresh_token

    def test_refresh_token_invalid(self, client: TestClient):
        response = client.post(
            "/auth/refresh", json={"refresh_token": "invalid_token_string"}
        )
        assert response.status_code == 401


class TestGetMe:
    def test_get_me_volunteer(self, session: Session, client: TestClient):
        # Create user & volunteer profile
        user_in = UserCreate(
            username="me_user",
            email="me@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user = user_service.create_user(session, user_in)

        from app.models.volunteer import Volunteer
        from datetime import date

        vol = Volunteer(
            id_user=user.id_user,
            first_name="Me",
            last_name="User",
            phone_number="123",
            birthdate=date(1990, 1, 1),
        )
        session.add(vol)
        session.commit()

        # Login
        login_res = client.post(
            "/auth/token", data={"username": "me_user", "password": "Password123"}
        )
        token = login_res.json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "volunteer"
        assert data["user"]["username"] == "me_user"
        assert data["profile"]["first_name"] == "Me"

    def test_get_me_unauthorized(self, client: TestClient):
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestPasswordReset:
    def test_request_password_reset(self, session: Session, client: TestClient):
        # Create user
        user_in = UserCreate(
            username="reset_user",
            email="reset@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user_service.create_user(session, user_in)

        with patch(
            "app.routers.auth.send_password_reset_email", new_callable=AsyncMock
        ) as mock_email:
            response = client.post(
                "/auth/password-reset/request", json={"email": "reset@example.com"}
            )
            assert response.status_code == 200
            mock_email.assert_called_once()

    def test_confirm_password_reset(self, session: Session, client: TestClient):
        # Create user
        user_in = UserCreate(
            username="confirm_user",
            email="confirm@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user = user_service.create_user(session, user_in)

        # Create token manually
        user, token = user_service.create_password_reset_token(session, user.email)

        with patch("app.services.user.reset_password_with_token") as mock_reset:
            response = client.post(
                "/auth/password-reset/confirm",
                json={"token": token, "new_password": "NewPassword123"},
            )
            assert response.status_code == 200
            mock_reset.assert_called_once()

        # Verify login with OLD password because service was mocked
        # login_res = client.post(...) # Not needed as we mocked the reset
