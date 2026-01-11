"""Tests for category router endpoints."""

from sqlmodel import Session
from fastapi.testclient import TestClient
from app.models.category import CategoryCreate
from app.services import category as category_service

# Test constants
CATEGORY_LABEL_HEALTH = "Health"
CATEGORY_LABEL_EDUCATION = "Education"


class TestGetCategories:
    """Test the GET /categories/ endpoint."""

    def test_get_all_categories_sorted(self, session: Session, client: TestClient):
        """Verify that the endpoint returns a list of categories sorted alphabetically."""
        # Arrange: Create categories in non-alphabetical order
        category_service.create_category(
            session, CategoryCreate(label=CATEGORY_LABEL_HEALTH)
        )
        category_service.create_category(
            session, CategoryCreate(label=CATEGORY_LABEL_EDUCATION)
        )

        # Act
        response = client.get("/categories/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Verify alphabetical order (Education comes before Health)
        assert data[0]["label"] == CATEGORY_LABEL_EDUCATION
        assert data[1]["label"] == CATEGORY_LABEL_HEALTH
        assert "id_categ" in data[0]

    def test_get_all_categories_empty(self, client: TestClient):
        """Verify that the endpoint returns an empty list when no categories exist in database."""
        response = client.get("/categories/")
        assert response.status_code == 200
        assert response.json() == []
