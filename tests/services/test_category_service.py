"""Tests for category service CRUD operations."""

import pytest
from sqlmodel import Session

from app.models.category import Category, CategoryCreate, CategoryUpdate
from app.services import category as category_service
from app.exceptions import NotFoundError, AlreadyExistsError

# Test data constants
TEST_CATEGORY_LABEL = "Environment"
TEST_CATEGORY_LABEL_2 = "Education"
TEST_CATEGORY_LABEL_3 = "Health"
TEST_LABEL_UPDATED = "Environment & Sustainability"
NONEXISTENT_ID = 99999


# Fixtures
@pytest.fixture(name="sample_category_create")
def sample_category_create_fixture():
    """
    Provide a standard CategoryCreate object populated with predefined test values.

    Returns:
        CategoryCreate: A CategoryCreate instance with the module's test label constant.
    """
    return CategoryCreate(label=TEST_CATEGORY_LABEL)


@pytest.fixture(name="created_category")
def created_category_fixture(
    session: Session, sample_category_create: CategoryCreate
) -> Category:
    """
    Create a Category record in the database for use in tests.

    Returns:
        Category: The created Category instance with a populated `id_categ`.
    """
    category = category_service.create_category(session, sample_category_create)
    assert category.id_categ is not None
    return category


@pytest.fixture(name="category_factory")
def category_factory_fixture(session: Session):
    """
    Provide a fixture that returns a factory for creating Category records with unique labels.

    Returns:
        factory: A callable _create_category(index=0) that creates a Category.
    """

    def _create_category(index: int = 0, **overrides) -> Category:
        data = {"label": f"Category_{index}"}
        data.update(overrides)
        category = category_service.create_category(session, CategoryCreate(**data))
        assert category.id_categ is not None
        return category

    return _create_category


class TestCreateCategory:
    """Test category creation."""

    def test_create_category_success(self, created_category: Category):
        """Test successful category creation."""
        assert created_category.id_categ is not None
        assert created_category.label == TEST_CATEGORY_LABEL

    def test_create_category_duplicate_label(
        self, session: Session, sample_category_create: CategoryCreate
    ):
        """Test that duplicate label raises AlreadyExistsError."""
        category_service.create_category(session, sample_category_create)

        with pytest.raises(AlreadyExistsError) as exc_info:
            category_service.create_category(session, sample_category_create)

        assert exc_info.value.resource == "Category"
        assert "already exists" in str(exc_info.value)


class TestGetCategory:
    """Test category retrieval operations."""

    def test_get_category_success(self, session: Session, created_category: Category):
        """Test retrieving a category by ID."""
        assert created_category.id_categ is not None
        found_category = category_service.get_category(
            session, created_category.id_categ
        )
        assert found_category is not None
        assert found_category.id_categ == created_category.id_categ
        assert found_category.label == created_category.label

    def test_get_category_not_found(self, session: Session):
        """Test retrieving a non-existent category."""
        found_category = category_service.get_category(session, NONEXISTENT_ID)
        assert found_category is None


class TestGetAllCategories:
    """Test listing categories."""

    def test_get_all_categories_empty(self, session: Session):
        """Test getting categories when database is empty."""
        categories = category_service.get_all_categories(session)
        assert categories == []

    def test_get_all_categories_multiple(self, session: Session, category_factory):
        """Test retrieving multiple categories."""
        # Create categories with labels that will sort predictably
        # "Category_0", "Category_1", "Category_2"
        for i in range(3):
            category_factory(i)

        categories = category_service.get_all_categories(session)
        assert len(categories) == 3
        assert all(isinstance(c, Category) for c in categories)
        # Verify order by label
        assert categories[0].label == "Category_0"
        assert categories[1].label == "Category_1"
        assert categories[2].label == "Category_2"


class TestUpdateCategory:
    """Test category update operations."""

    def test_update_category_success(
        self, session: Session, created_category: Category
    ):
        """Test updating category label."""
        assert created_category.id_categ is not None
        update_data = CategoryUpdate(label=TEST_LABEL_UPDATED)
        updated_category = category_service.update_category(
            session, created_category.id_categ, update_data
        )

        assert updated_category.label == TEST_LABEL_UPDATED
        # Verify persistence
        fetched_category = category_service.get_category(
            session, created_category.id_categ
        )
        assert fetched_category is not None
        assert fetched_category.label == TEST_LABEL_UPDATED

    def test_update_category_not_found(self, session: Session):
        """Test updating non-existent category raises NotFoundError."""
        update_data = CategoryUpdate(label=TEST_LABEL_UPDATED)
        with pytest.raises(NotFoundError) as exc_info:
            category_service.update_category(session, NONEXISTENT_ID, update_data)

        assert exc_info.value.resource == "Category"
        assert exc_info.value.identifier == NONEXISTENT_ID

    def test_update_category_duplicate_label(self, session: Session, category_factory):
        """Test updating to a label that already exists raises AlreadyExistsError."""
        _ = category_factory(1, label="Alpha")
        c2 = category_factory(2, label="Beta")
        assert c2.id_categ is not None

        update_data = CategoryUpdate(label="Alpha")
        with pytest.raises(AlreadyExistsError) as exc_info:
            category_service.update_category(session, c2.id_categ, update_data)

        assert exc_info.value.resource == "Category"
        assert "already exists" in str(exc_info.value)


class TestDeleteCategory:
    """Test category deletion."""

    def test_delete_category_success(
        self, session: Session, created_category: Category
    ):
        """Test successful category deletion."""
        assert created_category.id_categ is not None
        category_service.delete_category(session, created_category.id_categ)

        assert category_service.get_category(session, created_category.id_categ) is None

    def test_delete_category_not_found(self, session: Session):
        """Test deleting non-existent category raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            category_service.delete_category(session, NONEXISTENT_ID)

        assert exc_info.value.resource == "Category"
        assert exc_info.value.identifier == NONEXISTENT_ID
