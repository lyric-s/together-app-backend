"""Tests for admin service CRUD operations."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.models.admin import Admin, AdminCreate, AdminUpdate
from app.services import admin as admin_service
from app.core.password import verify_password

# Test data constants
TEST_ADMIN_USERNAME = "adminuser"
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_FIRST_NAME = "John"
TEST_ADMIN_LAST_NAME = "Doe"
TEST_ADMIN_PASSWORD = "AdminPass123"
TEST_EMAIL_NEW = "newemail@example.com"
TEST_EMAIL_UPDATED = "updated@example.com"
NONEXISTENT_ID = 99999
NONEXISTENT_USERNAME = "nonexistent"
NONEXISTENT_EMAIL = "nonexistent@example.com"


# Fixtures
@pytest.fixture(name="sample_admin_create")
def sample_admin_create_fixture():
    """Sample admin creation data."""
    return AdminCreate(
        username=TEST_ADMIN_USERNAME,
        email=TEST_ADMIN_EMAIL,
        first_name=TEST_ADMIN_FIRST_NAME,
        last_name=TEST_ADMIN_LAST_NAME,
        password=TEST_ADMIN_PASSWORD,
    )


@pytest.fixture(name="created_admin")
def created_admin_fixture(session: Session, sample_admin_create: AdminCreate) -> Admin:
    """Create and return an admin with ID assertion already done."""
    admin = admin_service.create_admin(session, sample_admin_create)
    assert admin.id_admin is not None
    return admin


@pytest.fixture(name="admin_factory")
def admin_factory_fixture(session: Session):
    """Factory fixture for creating multiple admins with unique data."""

    def _create_admin(index: int = 0, **overrides) -> Admin:
        """Create an admin with optional field overrides."""
        data = {
            "username": f"admin{index}",
            "email": f"admin{index}@example.com",
            "first_name": f"First{index}",
            "last_name": f"Last{index}",
            "password": "Password123",
        }
        data.update(overrides)
        admin = admin_service.create_admin(session, AdminCreate(**data))
        assert admin.id_admin is not None
        return admin

    return _create_admin


class TestCreateAdmin:
    """Test admin creation."""

    def test_create_admin_success(self, created_admin: Admin):
        """Test successful admin creation with password hashing."""
        assert created_admin.id_admin is not None
        assert created_admin.username == TEST_ADMIN_USERNAME
        assert created_admin.email == TEST_ADMIN_EMAIL
        assert created_admin.first_name == TEST_ADMIN_FIRST_NAME
        assert created_admin.last_name == TEST_ADMIN_LAST_NAME
        assert created_admin.hashed_password != TEST_ADMIN_PASSWORD
        assert verify_password(TEST_ADMIN_PASSWORD, created_admin.hashed_password)

    def test_create_admin_duplicate_username(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test that duplicate username raises HTTPException."""
        admin_service.create_admin(session, sample_admin_create)

        duplicate_admin = AdminCreate(
            username=TEST_ADMIN_USERNAME,  # Same username
            email="different@example.com",
            first_name="Jane",
            last_name="Smith",
            password="AnotherPass123",
        )

        with pytest.raises(HTTPException) as exc_info:
            admin_service.create_admin(session, duplicate_admin)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_create_admin_duplicate_email(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test that duplicate email raises HTTPException."""
        admin_service.create_admin(session, sample_admin_create)

        duplicate_email_admin = AdminCreate(
            username="differentadmin",
            email=TEST_ADMIN_EMAIL,  # Same email
            first_name="Jane",
            last_name="Smith",
            password="AnotherPass123",
        )

        with pytest.raises(HTTPException) as exc_info:
            admin_service.create_admin(session, duplicate_email_admin)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail


class TestGetAdmin:
    """Test admin retrieval operations."""

    @pytest.mark.parametrize(
        "getter_func,getter_arg,expected_field",
        [
            (admin_service.get_admin, lambda admin: admin.id_admin, "id_admin"),
            (
                admin_service.get_admin_by_username,
                lambda admin: admin.username,
                "username",
            ),
            (admin_service.get_admin_by_email, lambda admin: admin.email, "email"),
        ],
    )
    def test_get_admin_success(
        self,
        session: Session,
        created_admin: Admin,
        getter_func,
        getter_arg,
        expected_field,
    ):
        """Test successful admin retrieval by different fields."""
        retrieved_admin = getter_func(session, getter_arg(created_admin))

        assert retrieved_admin is not None
        assert retrieved_admin.id_admin == created_admin.id_admin
        assert getattr(retrieved_admin, expected_field) == getattr(
            created_admin, expected_field
        )

    @pytest.mark.parametrize(
        "getter_func,not_found_arg",
        [
            (admin_service.get_admin, NONEXISTENT_ID),
            (admin_service.get_admin_by_username, NONEXISTENT_USERNAME),
            (admin_service.get_admin_by_email, NONEXISTENT_EMAIL),
        ],
    )
    def test_get_admin_not_found(self, session: Session, getter_func, not_found_arg):
        """Test that non-existent admin returns None."""
        admin = getter_func(session, not_found_arg)
        assert admin is None


class TestGetAdmins:
    """Test paginated admin listing."""

    def test_get_admins_empty(self, session: Session):
        """Test getting admins when database is empty."""
        admins = admin_service.get_admins(session)
        assert admins == []

    def test_get_admins_multiple(self, session: Session, admin_factory):
        """Test retrieving multiple admins."""
        for i in range(3):
            admin_factory(i)

        admins = admin_service.get_admins(session)
        assert len(admins) == 3
        assert all(isinstance(admin, Admin) for admin in admins)

    @pytest.mark.parametrize(
        "total_count,offset,limit,expected_count",
        [
            (5, 2, None, 3),  # offset only
            (5, None, 2, 2),  # limit only
            (10, 3, 4, 4),  # offset and limit
        ],
    )
    def test_get_admins_pagination(
        self,
        session: Session,
        admin_factory,
        total_count,
        offset,
        limit,
        expected_count,
    ):
        """Test pagination with various offset and limit combinations."""
        for i in range(total_count):
            admin_factory(i)

        kwargs = {}
        if offset is not None:
            kwargs["offset"] = offset
        if limit is not None:
            kwargs["limit"] = limit

        admins = admin_service.get_admins(session, **kwargs)
        assert len(admins) == expected_count


class TestUpdateAdmin:
    """Test admin update operations."""

    def test_update_admin_email(self, session: Session, created_admin: Admin):
        """Test updating admin email."""
        assert created_admin.id_admin is not None
        update_data = AdminUpdate(email=TEST_EMAIL_NEW)
        updated_admin = admin_service.update_admin(
            session, created_admin.id_admin, update_data
        )

        assert updated_admin.email == TEST_EMAIL_NEW
        assert updated_admin.username == created_admin.username

    def test_update_admin_password(self, session: Session, created_admin: Admin):
        """Test updating admin password with proper hashing."""
        assert created_admin.id_admin is not None
        old_password_hash = created_admin.hashed_password

        new_password = "NewAdminPass456"
        update_data = AdminUpdate(password=new_password)
        updated_admin = admin_service.update_admin(
            session, created_admin.id_admin, update_data
        )

        assert updated_admin.hashed_password != old_password_hash
        assert verify_password(new_password, updated_admin.hashed_password)

    def test_update_admin_name(self, session: Session, created_admin: Admin):
        """Test updating admin first and last name."""
        assert created_admin.id_admin is not None
        new_first_name = "Jane"
        new_last_name = "Smith"
        update_data = AdminUpdate(first_name=new_first_name, last_name=new_last_name)
        updated_admin = admin_service.update_admin(
            session, created_admin.id_admin, update_data
        )

        assert updated_admin.first_name == new_first_name
        assert updated_admin.last_name == new_last_name

    def test_update_admin_multiple_fields(self, session: Session, created_admin: Admin):
        """Test updating multiple fields at once."""
        assert created_admin.id_admin is not None
        new_first_name = "Jane"
        new_last_name = "Smith"
        new_password = "UpdatedPass789"

        update_data = AdminUpdate(
            email=TEST_EMAIL_UPDATED,
            first_name=new_first_name,
            last_name=new_last_name,
            password=new_password,
        )
        updated_admin = admin_service.update_admin(
            session, created_admin.id_admin, update_data
        )

        assert updated_admin.email == TEST_EMAIL_UPDATED
        assert updated_admin.first_name == new_first_name
        assert updated_admin.last_name == new_last_name
        assert verify_password(new_password, updated_admin.hashed_password)

    def test_update_admin_not_found(self, session: Session):
        """Test updating non-existent admin raises HTTPException."""
        update_data = AdminUpdate(email=TEST_EMAIL_NEW)

        with pytest.raises(HTTPException) as exc_info:
            admin_service.update_admin(session, NONEXISTENT_ID, update_data)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_update_admin_duplicate_email(self, session: Session, admin_factory):
        """Test that updating to duplicate email raises HTTPException."""
        admin1 = admin_factory(1, username="admin1", email="admin1@example.com")
        admin2_email = "admin2@example.com"
        admin_factory(2, username="admin2", email=admin2_email)

        update_data = AdminUpdate(email=admin2_email)

        with pytest.raises(HTTPException) as exc_info:
            admin_service.update_admin(session, admin1.id_admin, update_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_update_admin_partial(self, session: Session, created_admin: Admin):
        """Test that only provided fields are updated (exclude_unset)."""
        assert created_admin.id_admin is not None
        original_email = created_admin.email
        original_last_name = created_admin.last_name

        new_first_name = "UpdatedName"
        update_data = AdminUpdate(first_name=new_first_name)
        updated_admin = admin_service.update_admin(
            session, created_admin.id_admin, update_data
        )

        assert updated_admin.first_name == new_first_name
        assert updated_admin.email == original_email
        assert updated_admin.last_name == original_last_name


class TestDeleteAdmin:
    """Test admin deletion."""

    def test_delete_admin_success(self, session: Session, created_admin: Admin):
        """Test successful admin deletion."""
        assert created_admin.id_admin is not None
        admin_id = created_admin.id_admin

        admin_service.delete_admin(session, admin_id)

        deleted_admin = admin_service.get_admin(session, admin_id)
        assert deleted_admin is None

    def test_delete_admin_not_found(self, session: Session):
        """Test deleting non-existent admin raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            admin_service.delete_admin(session, NONEXISTENT_ID)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
