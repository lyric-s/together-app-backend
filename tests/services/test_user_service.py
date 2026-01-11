"""Tests for user service CRUD operations. Generated and validated."""

import pytest
from sqlmodel import Session

from app.models.user import User, UserCreate, UserUpdate
from app.models.enums import UserType
from app.services import user as user_service
from app.core.password import verify_password
from app.exceptions import NotFoundError, AlreadyExistsError

# Test data constants
TEST_USER_USERNAME = "testuser"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "SecurePass123"
TEST_EMAIL_NEW = "newemail@example.com"
TEST_EMAIL_UPDATED = "updated@example.com"
NONEXISTENT_ID = 99999
NONEXISTENT_USERNAME = "nonexistent"
NONEXISTENT_EMAIL = "nonexistent@example.com"


# Fixtures
@pytest.fixture(name="sample_user_create")
def sample_user_create_fixture():
    """
    Provide a UserCreate payload populated with standard test user attributes.

    Returns:
        UserCreate: Instance initialized with TEST_USER_USERNAME, TEST_USER_EMAIL, TEST_USER_PASSWORD, and UserType.VOLUNTEER.
    """
    return UserCreate(
        username=TEST_USER_USERNAME,
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        user_type=UserType.VOLUNTEER,
    )


@pytest.fixture(name="created_user")
def created_user_fixture(session: Session, sample_user_create: UserCreate) -> User:
    """
    Create a new user from a UserCreate payload and return the created User.

    Parameters:
        session (Session): Database session used to persist the user.
        sample_user_create (UserCreate): Payload containing username, email, password, and user_type.

    Returns:
        User: The persisted user instance with `id_user` populated.
    """
    user = user_service.create_user(session, sample_user_create)
    assert user.id_user is not None
    return user


@pytest.fixture(name="user_factory")
def user_factory_fixture(session: Session):
    """
    Return a factory callable that creates test User records with unique default attributes.

    The returned callable creates a User using sensible defaults (username/email/password/user_type) and asserts the created user's `id_user` is not None.

    Returns:
        Callable[[int, **dict], User]: A factory function that creates and returns a User instance.
    """
    """
    Create a test User, allowing optional field overrides.

    Parameters:
        index (int): Numeric suffix used to generate a unique default username and email (e.g., "user0", "user0@example.com").
        **overrides: Field values to override the defaults accepted by UserCreate (e.g., email="x@example.com", password="...").

    Returns:
        User: The created User instance; `id_user` is guaranteed to be non-None by an assertion.
    """

    def _create_user(index: int = 0, **overrides) -> User:
        """
        Create and persist a test user with predictable credentials, allowing field overrides.

        Parameters:
            index (int): Numeric suffix used to generate default `username` and `email` (e.g., "user0", "user0@example.com").
            overrides (dict): Field values to override the defaults; keys correspond to UserCreate fields (e.g., "email", "password", "user_type").

        Returns:
            User: The created User instance with a non-null `id_user`.
        """
        data = {
            "username": f"user{index}",
            "email": f"user{index}@example.com",
            "password": "Password123",
            "user_type": UserType.VOLUNTEER,
        }
        data.update(overrides)
        user = user_service.create_user(session, UserCreate(**data))
        assert user.id_user is not None
        return user

    return _create_user


class TestCreateUser:
    """Test user creation."""

    def test_create_user_success(self, created_user: User):
        """Test successful user creation with password hashing."""
        assert created_user.id_user is not None
        assert created_user.username == TEST_USER_USERNAME
        assert created_user.email == TEST_USER_EMAIL
        assert created_user.user_type == UserType.VOLUNTEER
        assert created_user.hashed_password != TEST_USER_PASSWORD
        assert verify_password(TEST_USER_PASSWORD, created_user.hashed_password)
        assert created_user.date_creation is not None

    def test_create_user_duplicate_username(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test that duplicate username raises AlreadyExistsError."""
        user_service.create_user(session, sample_user_create)

        duplicate_user = UserCreate(
            username=TEST_USER_USERNAME,  # Same username
            email="different@example.com",
            password="AnotherPass123",
            user_type=UserType.VOLUNTEER,
        )

        with pytest.raises(AlreadyExistsError) as exc_info:
            user_service.create_user(session, duplicate_user)

        assert exc_info.value.resource == "User"
        assert "already exists" in str(exc_info.value)

    def test_create_user_duplicate_email(
        self, session: Session, sample_user_create: UserCreate
    ):
        """Test that duplicate email raises AlreadyExistsError."""
        user_service.create_user(session, sample_user_create)

        duplicate_user = UserCreate(
            username="differentuser",
            email=TEST_USER_EMAIL,  # Same email
            password="AnotherPass123",
            user_type=UserType.VOLUNTEER,
        )

        with pytest.raises(AlreadyExistsError) as exc_info:
            user_service.create_user(session, duplicate_user)

        assert exc_info.value.resource == "User"
        assert "already exists" in str(exc_info.value)


class TestGetUser:
    """Test user retrieval operations."""

    @pytest.mark.parametrize(
        "getter_func,getter_arg,expected_field",
        [
            (user_service.get_user, lambda user: user.id_user, "id_user"),
            (user_service.get_user_by_username, lambda user: user.username, "username"),
            (user_service.get_user_by_email, lambda user: user.email, "email"),
        ],
    )
    def test_get_user_success(
        self,
        session: Session,
        created_user: User,
        getter_func,
        getter_arg,
        expected_field,
    ):
        """
        Verify that a user can be retrieved using the provided getter and that the retrieved user's id and a specified field match the created user.

        Parameters:
            getter_func: Callable that takes (Session, identifier) and returns a User or None.
            getter_arg: Callable that, given the created User, returns the identifier to pass to `getter_func`.
            expected_field (str): Name of the attribute on the User that must match between created and retrieved instances.
        """
        retrieved_user = getter_func(session, getter_arg(created_user))

        assert retrieved_user is not None
        assert retrieved_user.id_user == created_user.id_user
        assert getattr(retrieved_user, expected_field) == getattr(
            created_user, expected_field
        )

    @pytest.mark.parametrize(
        "getter_func,not_found_arg",
        [
            (user_service.get_user, NONEXISTENT_ID),
            (user_service.get_user_by_username, NONEXISTENT_USERNAME),
            (user_service.get_user_by_email, NONEXISTENT_EMAIL),
        ],
    )
    def test_get_user_not_found(self, session: Session, getter_func, not_found_arg):
        """
        Verify that attempting to retrieve a non-existent user produces no result.

        Parameters:
                getter_func (callable): User retrieval function to call with (session, identifier).
                not_found_arg (Any): Identifier value that does not exist in the database.
        """
        user = getter_func(session, not_found_arg)
        assert user is None


class TestGetUsers:
    """Test paginated user listing."""

    def test_get_users_empty(self, session: Session):
        """Test getting users when database is empty."""
        users = user_service.get_users(session)
        assert users == []

    def test_get_users_multiple(self, session: Session, user_factory):
        """Test retrieving multiple users."""
        for i in range(3):
            user_factory(i)

        users = user_service.get_users(session)
        assert len(users) == 3
        assert all(isinstance(user, User) for user in users)

    @pytest.mark.parametrize(
        "total_count,offset,limit,expected_count",
        [
            (5, 2, None, 3),  # offset only
            (5, None, 2, 2),  # limit only
            (10, 3, 4, 4),  # offset and limit
        ],
    )
    def test_get_users_pagination(
        self, session: Session, user_factory, total_count, offset, limit, expected_count
    ):
        """Test pagination with various offset and limit combinations."""
        for i in range(total_count):
            user_factory(i)

        kwargs = {}
        if offset is not None:
            kwargs["offset"] = offset
        if limit is not None:
            kwargs["limit"] = limit

        users = user_service.get_users(session, **kwargs)
        assert len(users) == expected_count


class TestUpdateUser:
    """Test user update operations."""

    def test_update_user_email(self, session: Session, created_user: User):
        """Test updating user email."""
        assert created_user.id_user is not None
        update_data = UserUpdate(email=TEST_EMAIL_NEW)
        updated_user = user_service.update_user(
            session, created_user.id_user, update_data
        )

        assert updated_user.email == TEST_EMAIL_NEW
        assert updated_user.username == created_user.username

    def test_update_user_password(self, session: Session, created_user: User):
        """Test updating user password with proper hashing."""
        assert created_user.id_user is not None
        old_password_hash = created_user.hashed_password

        new_password = "NewSecurePass456"
        update_data = UserUpdate(password=new_password)
        updated_user = user_service.update_user(
            session, created_user.id_user, update_data
        )

        assert updated_user.hashed_password != old_password_hash
        assert verify_password(new_password, updated_user.hashed_password)

    def test_update_user_user_type(self, session: Session, created_user: User):
        """Test updating user type."""
        assert created_user.id_user is not None
        update_data = UserUpdate(user_type=UserType.ASSOCIATION)
        updated_user = user_service.update_user(
            session, created_user.id_user, update_data
        )

        assert updated_user.user_type == UserType.ASSOCIATION

    def test_update_user_multiple_fields(self, session: Session, created_user: User):
        """Test updating multiple fields at once."""
        assert created_user.id_user is not None
        new_password = "UpdatedPass789"

        update_data = UserUpdate(
            email=TEST_EMAIL_UPDATED,
            password=new_password,
            user_type=UserType.ASSOCIATION,
        )
        updated_user = user_service.update_user(
            session, created_user.id_user, update_data
        )

        assert updated_user.email == TEST_EMAIL_UPDATED
        assert verify_password(new_password, updated_user.hashed_password)
        assert updated_user.user_type == UserType.ASSOCIATION

    def test_update_user_not_found(self, session: Session):
        """Test updating non-existent user raises NotFoundError."""
        update_data = UserUpdate(email=TEST_EMAIL_NEW)

        with pytest.raises(NotFoundError) as exc_info:
            user_service.update_user(session, NONEXISTENT_ID, update_data)

        assert exc_info.value.resource == "User"
        assert exc_info.value.identifier == NONEXISTENT_ID

    def test_update_user_duplicate_email(self, session: Session, user_factory):
        """Test that updating to duplicate email raises AlreadyExistsError."""
        user1 = user_factory(1, username="user1", email="user1@example.com")
        user2_email = "user2@example.com"
        user_factory(2, username="user2", email=user2_email)

        update_data = UserUpdate(email=user2_email)

        with pytest.raises(AlreadyExistsError) as exc_info:
            user_service.update_user(session, user1.id_user, update_data)

        assert exc_info.value.resource == "User"
        assert "already exists" in str(exc_info.value)

    def test_update_user_partial(self, session: Session, created_user: User):
        """Test that only provided fields are updated (exclude_unset)."""
        assert created_user.id_user is not None
        original_email = created_user.email

        update_data = UserUpdate(user_type=UserType.ASSOCIATION)
        updated_user = user_service.update_user(
            session, created_user.id_user, update_data
        )

        assert updated_user.user_type == UserType.ASSOCIATION
        assert updated_user.email == original_email


class TestDeleteUser:
    """Test user deletion."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self, session: Session, created_user: User):
        """Test successful user deletion."""
        assert created_user.id_user is not None
        user_id = created_user.id_user

        await user_service.delete_user(session, user_id)

        deleted_user = user_service.get_user(session, user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, session: Session):
        """Test deleting non-existent user raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            await user_service.delete_user(session, NONEXISTENT_ID)

        assert exc_info.value.resource == "User"
        assert exc_info.value.identifier == NONEXISTENT_ID
