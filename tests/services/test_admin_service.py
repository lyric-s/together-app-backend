"""Tests for admin service CRUD operations."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.models.admin import Admin, AdminCreate, AdminUpdate
from app.services import admin as admin_service
from app.core.password import verify_password


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="sample_admin_create")
def sample_admin_create_fixture():
    """Sample admin creation data."""
    return AdminCreate(
        username="adminuser",
        email="admin@example.com",
        first_name="John",
        last_name="Doe",
        password="AdminPass123",
    )


class TestCreateAdmin:
    """Test admin creation."""

    def test_create_admin_success(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test successful admin creation with password hashing."""
        admin = admin_service.create_admin(session, sample_admin_create)

        assert admin.id_admin is not None
        assert admin.username == "adminuser"
        assert admin.email == "admin@example.com"
        assert admin.first_name == "John"
        assert admin.last_name == "Doe"
        assert admin.hashed_password != "AdminPass123"  # Password should be hashed
        assert verify_password("AdminPass123", admin.hashed_password)

    def test_create_admin_duplicate_username(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test that duplicate username raises HTTPException."""
        admin_service.create_admin(session, sample_admin_create)

        # Try to create another admin with same username
        duplicate_admin = AdminCreate(
            username="adminuser",  # Same username
            email="different@example.com",
            first_name="Jane",
            last_name="Smith",
            password="AnotherPass123",
        )

        with pytest.raises(HTTPException) as exc_info:
            admin_service.create_admin(session, duplicate_admin)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_create_admin_duplicate_email_allowed(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test that duplicate email is allowed (email is not unique for admins)."""
        admin_service.create_admin(session, sample_admin_create)

        # Create another admin with same email but different username
        duplicate_email_admin = AdminCreate(
            username="differentadmin",
            email="admin@example.com",  # Same email - this is allowed
            first_name="Jane",
            last_name="Smith",
            password="AnotherPass123",
        )

        # Should succeed - email is not unique for admins
        admin2 = admin_service.create_admin(session, duplicate_email_admin)
        assert admin2.email == "admin@example.com"


class TestGetAdmin:
    """Test admin retrieval operations."""

    def test_get_admin_by_id_success(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test successful admin retrieval by ID."""
        created_admin = admin_service.create_admin(session, sample_admin_create)
        assert created_admin.id_admin is not None

        retrieved_admin = admin_service.get_admin(session, created_admin.id_admin)

        assert retrieved_admin is not None
        assert retrieved_admin.id_admin == created_admin.id_admin
        assert retrieved_admin.username == created_admin.username

    def test_get_admin_by_id_not_found(self, session: Session):
        """Test that non-existent admin returns None."""
        admin = admin_service.get_admin(session, 99999)
        assert admin is None

    def test_get_admin_by_username_success(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test successful admin retrieval by username."""
        created_admin = admin_service.create_admin(session, sample_admin_create)

        retrieved_admin = admin_service.get_admin_by_username(session, "adminuser")

        assert retrieved_admin is not None
        assert retrieved_admin.id_admin == created_admin.id_admin
        assert retrieved_admin.username == "adminuser"

    def test_get_admin_by_username_not_found(self, session: Session):
        """Test that non-existent username returns None."""
        admin = admin_service.get_admin_by_username(session, "nonexistent")
        assert admin is None

    def test_get_admin_by_email_success(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test successful admin retrieval by email."""
        created_admin = admin_service.create_admin(session, sample_admin_create)

        retrieved_admin = admin_service.get_admin_by_email(session, "admin@example.com")

        assert retrieved_admin is not None
        assert retrieved_admin.id_admin == created_admin.id_admin
        assert retrieved_admin.email == "admin@example.com"

    def test_get_admin_by_email_not_found(self, session: Session):
        """Test that non-existent email returns None."""
        admin = admin_service.get_admin_by_email(session, "nonexistent@example.com")
        assert admin is None


class TestGetAdmins:
    """Test paginated admin listing."""

    def test_get_admins_empty(self, session: Session):
        """Test getting admins when database is empty."""
        admins = admin_service.get_admins(session)
        assert admins == []

    def test_get_admins_multiple(self, session: Session):
        """Test retrieving multiple admins."""
        # Create 3 admins
        for i in range(3):
            admin_create = AdminCreate(
                username=f"admin{i}",
                email=f"admin{i}@example.com",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                password="Password123",
            )
            admin_service.create_admin(session, admin_create)

        admins = admin_service.get_admins(session)

        assert len(admins) == 3
        assert all(isinstance(admin, Admin) for admin in admins)

    def test_get_admins_pagination_offset(self, session: Session):
        """Test pagination with offset."""
        # Create 5 admins
        for i in range(5):
            admin_create = AdminCreate(
                username=f"admin{i}",
                email=f"admin{i}@example.com",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                password="Password123",
            )
            admin_service.create_admin(session, admin_create)

        admins = admin_service.get_admins(session, offset=2)

        assert len(admins) == 3  # Should get admins 2, 3, 4

    def test_get_admins_pagination_limit(self, session: Session):
        """Test pagination with limit."""
        # Create 5 admins
        for i in range(5):
            admin_create = AdminCreate(
                username=f"admin{i}",
                email=f"admin{i}@example.com",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                password="Password123",
            )
            admin_service.create_admin(session, admin_create)

        admins = admin_service.get_admins(session, limit=2)

        assert len(admins) == 2

    def test_get_admins_pagination_offset_and_limit(self, session: Session):
        """Test pagination with both offset and limit."""
        # Create 10 admins
        for i in range(10):
            admin_create = AdminCreate(
                username=f"admin{i}",
                email=f"admin{i}@example.com",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                password="Password123",
            )
            admin_service.create_admin(session, admin_create)

        admins = admin_service.get_admins(session, offset=3, limit=4)

        assert len(admins) == 4


class TestUpdateAdmin:
    """Test admin update operations."""

    def test_update_admin_email(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test updating admin email."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None

        update_data = AdminUpdate(email="newemail@example.com")
        updated_admin = admin_service.update_admin(session, admin.id_admin, update_data)

        assert updated_admin.email == "newemail@example.com"
        assert updated_admin.username == admin.username  # Should remain unchanged

    def test_update_admin_password(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test updating admin password with proper hashing."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None
        old_password_hash = admin.hashed_password

        update_data = AdminUpdate(password="NewAdminPass456")
        updated_admin = admin_service.update_admin(session, admin.id_admin, update_data)

        assert updated_admin.hashed_password != old_password_hash
        assert verify_password("NewAdminPass456", updated_admin.hashed_password)

    def test_update_admin_name(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test updating admin first and last name."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None

        update_data = AdminUpdate(first_name="Jane", last_name="Smith")
        updated_admin = admin_service.update_admin(session, admin.id_admin, update_data)

        assert updated_admin.first_name == "Jane"
        assert updated_admin.last_name == "Smith"

    def test_update_admin_multiple_fields(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test updating multiple fields at once."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None

        update_data = AdminUpdate(
            email="updated@example.com",
            first_name="Jane",
            last_name="Smith",
            password="UpdatedPass789",
        )
        updated_admin = admin_service.update_admin(session, admin.id_admin, update_data)

        assert updated_admin.email == "updated@example.com"
        assert updated_admin.first_name == "Jane"
        assert updated_admin.last_name == "Smith"
        assert verify_password("UpdatedPass789", updated_admin.hashed_password)

    def test_update_admin_not_found(self, session: Session):
        """Test updating non-existent admin raises HTTPException."""
        update_data = AdminUpdate(email="newemail@example.com")

        with pytest.raises(HTTPException) as exc_info:
            admin_service.update_admin(session, 99999, update_data)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_update_admin_duplicate_email_allowed(self, session: Session):
        """Test that updating to duplicate email is allowed (email is not unique for admins)."""
        # Create two admins
        admin1_create = AdminCreate(
            username="admin1",
            email="admin1@example.com",
            first_name="John",
            last_name="Doe",
            password="Password123",
        )
        admin2_create = AdminCreate(
            username="admin2",
            email="admin2@example.com",
            first_name="Jane",
            last_name="Smith",
            password="Password123",
        )
        admin1 = admin_service.create_admin(session, admin1_create)
        assert admin1.id_admin is not None
        admin_service.create_admin(session, admin2_create)

        # Update admin1's email to admin2's email - should succeed
        update_data = AdminUpdate(email="admin2@example.com")
        updated_admin = admin_service.update_admin(
            session, admin1.id_admin, update_data
        )

        assert updated_admin.email == "admin2@example.com"

    def test_update_admin_partial(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test that only provided fields are updated (exclude_unset)."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None
        original_email = admin.email
        original_last_name = admin.last_name

        # Only update first_name, other fields should remain unchanged
        update_data = AdminUpdate(first_name="UpdatedName")
        updated_admin = admin_service.update_admin(session, admin.id_admin, update_data)

        assert updated_admin.first_name == "UpdatedName"
        assert updated_admin.email == original_email
        assert updated_admin.last_name == original_last_name


class TestDeleteAdmin:
    """Test admin deletion."""

    def test_delete_admin_success(
        self, session: Session, sample_admin_create: AdminCreate
    ):
        """Test successful admin deletion."""
        admin = admin_service.create_admin(session, sample_admin_create)
        assert admin.id_admin is not None
        admin_id = admin.id_admin

        admin_service.delete_admin(session, admin_id)

        # Verify admin is deleted
        deleted_admin = admin_service.get_admin(session, admin_id)
        assert deleted_admin is None

    def test_delete_admin_not_found(self, session: Session):
        """Test deleting non-existent admin raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            admin_service.delete_admin(session, 99999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
