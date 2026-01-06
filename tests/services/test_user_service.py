"""Tests for user service CRUD operations."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.models.user import User, UserCreate, UserUpdate
from app.models.enums import UserType
from app.services import user as user_service
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


@pytest.fixture(name="sample_user_create")
def sample_user_create_fixture():
    """Sample user creation data."""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        password="SecurePass123",
        user_type=UserType.VOLUNTEER,
    )


class TestCreateUser:
    """Test user creation."""

    def test_create_user_success(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test successful user creation with password hashing."""
        user = user_service.create_user(session, sample_user_create)

        assert user.id_user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.user_type == UserType.VOLUNTEER
        assert user.hashed_password != "SecurePass123"  # Password should be hashed
        assert verify_password("SecurePass123", user.hashed_password)
        assert user.date_creation is not None

    def test_create_user_duplicate_username(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test that duplicate username raises HTTPException."""
        user_service.create_user(session, sample_user_create)

        # Try to create another user with same username
        duplicate_user = UserCreate(
            username="testuser",  # Same username
            email="different@example.com",
            password="AnotherPass123",
            user_type=UserType.VOLUNTEER,
        )

        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user(session, duplicate_user)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_create_user_duplicate_email(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test that duplicate email raises HTTPException."""
        user_service.create_user(session, sample_user_create)

        # Try to create another user with same email
        duplicate_user = UserCreate(
            username="differentuser",
            email="test@example.com",  # Same email
            password="AnotherPass123",
            user_type=UserType.VOLUNTEER,
        )

        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user(session, duplicate_user)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail


class TestGetUser:
    """Test user retrieval operations."""

    def test_get_user_by_id_success(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test successful user retrieval by ID."""
        created_user = user_service.create_user(session, sample_user_create)
        assert created_user.id_user is not None

        retrieved_user = user_service.get_user(session, created_user.id_user)

        assert retrieved_user is not None
        assert retrieved_user.id_user == created_user.id_user
        assert retrieved_user.username == created_user.username

    def test_get_user_by_id_not_found(self, session: Session):
        """Test that non-existent user returns None."""
        user = user_service.get_user(session, 99999)
        assert user is None

    def test_get_user_by_username_success(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test successful user retrieval by username."""
        created_user = user_service.create_user(session, sample_user_create)

        retrieved_user = user_service.get_user_by_username(session, "testuser")

        assert retrieved_user is not None
        assert retrieved_user.id_user == created_user.id_user
        assert retrieved_user.username == "testuser"

    def test_get_user_by_username_not_found(self, session: Session):
        """Test that non-existent username returns None."""
        user = user_service.get_user_by_username(session, "nonexistent")
        assert user is None

    def test_get_user_by_email_success(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test successful user retrieval by email."""
        created_user = user_service.create_user(session, sample_user_create)

        retrieved_user = user_service.get_user_by_email(session, "test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.id_user == created_user.id_user
        assert retrieved_user.email == "test@example.com"

    def test_get_user_by_email_not_found(self, session: Session):
        """Test that non-existent email returns None."""
        user = user_service.get_user_by_email(session, "nonexistent@example.com")
        assert user is None


class TestGetUsers:
    """Test paginated user listing."""

    def test_get_users_empty(self, session: Session):
        """Test getting users when database is empty."""
        users = user_service.get_users(session)
        assert users == []

    def test_get_users_multiple(self, session: Session):
        """Test retrieving multiple users."""
        # Create 3 users
        for i in range(3):
            user_create = UserCreate(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            )
            user_service.create_user(session, user_create)

        users = user_service.get_users(session)

        assert len(users) == 3
        assert all(isinstance(user, User) for user in users)

    def test_get_users_pagination_offset(self, session: Session):
        """Test pagination with offset."""
        # Create 5 users
        for i in range(5):
            user_create = UserCreate(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            )
            user_service.create_user(session, user_create)

        users = user_service.get_users(session, offset=2)

        assert len(users) == 3  # Should get users 2, 3, 4

    def test_get_users_pagination_limit(self, session: Session):
        """Test pagination with limit."""
        # Create 5 users
        for i in range(5):
            user_create = UserCreate(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            )
            user_service.create_user(session, user_create)

        users = user_service.get_users(session, limit=2)

        assert len(users) == 2

    def test_get_users_pagination_offset_and_limit(self, session: Session):
        """Test pagination with both offset and limit."""
        # Create 10 users
        for i in range(10):
            user_create = UserCreate(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            )
            user_service.create_user(session, user_create)

        users = user_service.get_users(session, offset=3, limit=4)

        assert len(users) == 4


class TestUpdateUser:
    """Test user update operations."""

    def test_update_user_email(self, session: Session, sample_user_create: UserCreate):
        """Test updating user email."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None

        update_data = UserUpdate(email="newemail@example.com")
        updated_user = user_service.update_user(session, user.id_user, update_data)

        assert updated_user.email == "newemail@example.com"
        assert updated_user.username == user.username  # Should remain unchanged

    def test_update_user_password(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test updating user password with proper hashing."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None
        old_password_hash = user.hashed_password

        update_data = UserUpdate(password="NewSecurePass456")
        updated_user = user_service.update_user(session, user.id_user, update_data)

        assert updated_user.hashed_password != old_password_hash
        assert verify_password("NewSecurePass456", updated_user.hashed_password)

    def test_update_user_user_type(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test updating user type."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None

        update_data = UserUpdate(user_type=UserType.ASSOCIATION)
        updated_user = user_service.update_user(session, user.id_user, update_data)

        assert updated_user.user_type == UserType.ASSOCIATION

    def test_update_user_multiple_fields(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test updating multiple fields at once."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None

        update_data = UserUpdate(
            email="updated@example.com",
            password="UpdatedPass789",
            user_type=UserType.ASSOCIATION,
        )
        updated_user = user_service.update_user(session, user.id_user, update_data)

        assert updated_user.email == "updated@example.com"
        assert verify_password("UpdatedPass789", updated_user.hashed_password)
        assert updated_user.user_type == UserType.ASSOCIATION

    def test_update_user_not_found(self, session: Session):
        """Test updating non-existent user raises HTTPException."""
        update_data = UserUpdate(email="newemail@example.com")

        with pytest.raises(HTTPException) as exc_info:
            user_service.update_user(session, 99999, update_data)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_update_user_duplicate_email(self, session: Session):
        """Test that updating to duplicate email raises HTTPException."""
        # Create two users
        user1_create = UserCreate(
            username="user1",
            email="user1@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user2_create = UserCreate(
            username="user2",
            email="user2@example.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user1 = user_service.create_user(session, user1_create)
        assert user1.id_user is not None
        user_service.create_user(session, user2_create)

        # Try to update user1's email to user2's email
        update_data = UserUpdate(email="user2@example.com")

        with pytest.raises(HTTPException) as exc_info:
            user_service.update_user(session, user1.id_user, update_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    def test_update_user_partial(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test that only provided fields are updated (exclude_unset)."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None
        original_email = user.email

        # Only update user_type, email should remain unchanged
        update_data = UserUpdate(user_type=UserType.ASSOCIATION)
        updated_user = user_service.update_user(session, user.id_user, update_data)

        assert updated_user.user_type == UserType.ASSOCIATION
        assert updated_user.email == original_email


class TestDeleteUser:
    """Test user deletion."""

    def test_delete_user_success(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test successful user deletion."""
        user = user_service.create_user(session, sample_user_create)
        assert user.id_user is not None
        user_id = user.id_user

        user_service.delete_user(session, user_id)

        # Verify user is deleted
        deleted_user = user_service.get_user(session, user_id)
        assert deleted_user is None

    def test_delete_user_not_found(self, session: Session):
        """Test deleting non-existent user raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            user_service.delete_user(session, 99999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
