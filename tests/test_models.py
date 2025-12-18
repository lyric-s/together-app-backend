import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.user import User, UserBase, UserCreate, UserPublic, UserUpdate
from app.models.admin import Admin, AdminBase, AdminCreate, AdminPublic, AdminUpdate
from app.models.token import Token, TokenData, TokenRefreshRequest
from app.models.enums import UserType, ProcessingStatus


class TestUserModels:
    """Test User model and related schemas."""

    def test_user_base_creation(self):
        """Test UserBase model creation."""
        user_base = UserBase(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER
        )
        assert user_base.username == "testuser"
        assert user_base.email == "test@example.com"
        assert user_base.user_type == UserType.VOLUNTEER

    def test_user_base_with_enum_string(self):
        """Test UserBase with enum as string."""
        user_base = UserBase(
            username="testuser",
            email="test@example.com",
            user_type="volunteer"
        )
        assert user_base.user_type == UserType.VOLUNTEER

    def test_user_create_with_password(self):
        """Test UserCreate includes password field."""
        user_create = UserCreate(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER,
            password="password123"
        )
        assert user_create.password == "password123"
        assert len(user_create.password) >= 8

    def test_user_create_short_password_validation(self):
        """Test that password shorter than 8 chars raises validation error."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                user_type=UserType.VOLUNTEER,
                password="short"  # Less than 8 characters
            )

    def test_user_create_minimum_password_length(self):
        """Test minimum password length of 8 characters."""
        user_create = UserCreate(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER,
            password="12345678"  # Exactly 8 characters
        )
        assert len(user_create.password) == 8

    def test_user_public_excludes_password(self):
        """Test that UserPublic doesn't include password fields."""
        user_public = UserPublic(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER,
            id_user=1,
            date_creation=datetime.now()
        )
        assert not hasattr(user_public, "password")
        assert not hasattr(user_public, "hashed_password")
        assert user_public.id_user == 1

    def test_user_update_optional_fields(self):
        """Test that UserUpdate has all optional fields."""
        user_update = UserUpdate()
        assert user_update.email is None
        assert user_update.user_type is None
        assert user_update.password is None

    def test_user_update_partial_update(self):
        """Test partial update with UserUpdate."""
        user_update = UserUpdate(email="newemail@example.com")
        assert user_update.email == "newemail@example.com"
        assert user_update.user_type is None
        assert user_update.password is None

    def test_user_with_different_user_types(self):
        """Test User with different user types."""
        for user_type in UserType:
            user_base = UserBase(
                username=f"user_{user_type.value}",
                email=f"{user_type.value}@example.com",
                user_type=user_type
            )
            assert user_base.user_type == user_type

    def test_user_email_validation(self):
        """Test email validation."""
        # Valid email
        user = UserBase(
            username="testuser",
            email="valid@example.com",
            user_type=UserType.VOLUNTEER
        )
        assert user.email == "valid@example.com"

    def test_user_with_special_characters_in_username(self):
        """Test username with special characters."""
        user = UserBase(
            username="user.name_123",
            email="test@example.com",
            user_type=UserType.VOLUNTEER
        )
        assert user.username == "user.name_123"


class TestAdminModels:
    """Test Admin model and related schemas."""

    def test_admin_base_creation(self):
        """Test AdminBase model creation."""
        admin_base = AdminBase(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            username="johndoe"
        )
        assert admin_base.first_name == "John"
        assert admin_base.last_name == "Doe"
        assert admin_base.email == "john.doe@example.com"
        assert admin_base.username == "johndoe"

    def test_admin_create_with_password(self):
        """Test AdminCreate includes password field."""
        admin_create = AdminCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            username="johndoe",
            password="securepassword"
        )
        assert admin_create.password == "securepassword"

    def test_admin_public_excludes_password(self):
        """Test that AdminPublic doesn't include password fields."""
        admin_public = AdminPublic(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            username="johndoe",
            id_admin=1
        )
        assert not hasattr(admin_public, "password")
        assert not hasattr(admin_public, "hashed_password")
        assert admin_public.id_admin == 1

    def test_admin_update_optional_fields(self):
        """Test that AdminUpdate has all optional fields."""
        admin_update = AdminUpdate()
        assert admin_update.first_name is None
        assert admin_update.last_name is None
        assert admin_update.email is None

    def test_admin_update_partial_update(self):
        """Test partial update with AdminUpdate."""
        admin_update = AdminUpdate(
            first_name="Jane",
            email="jane@example.com"
        )
        assert admin_update.first_name == "Jane"
        assert admin_update.email == "jane@example.com"
        assert admin_update.last_name is None

    def test_admin_name_max_length(self):
        """Test admin name fields with max length."""
        admin = AdminBase(
            first_name="A" * 50,
            last_name="B" * 50,
            email="test@example.com",
            username="testuser"
        )
        assert len(admin.first_name) == 50
        assert len(admin.last_name) == 50

    def test_admin_email_max_length(self):
        """Test admin email with max length."""
        long_email = "a" * 240 + "@example.com"  # Total 252 chars
        admin = AdminBase(
            first_name="John",
            last_name="Doe",
            email=long_email,
            username="johndoe"
        )
        assert len(admin.email) <= 255

    def test_admin_username_max_length(self):
        """Test admin username with max length."""
        admin = AdminBase(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            username="a" * 50
        )
        assert len(admin.username) == 50

    def test_admin_with_special_characters_in_name(self):
        """Test admin with special characters in name."""
        admin = AdminBase(
            first_name="Jean-Pierre",
            last_name="O'Brien",
            email="jp@example.com",
            username="jpobrien"
        )
        assert admin.first_name == "Jean-Pierre"
        assert admin.last_name == "O'Brien"


class TestTokenModels:
    """Test Token model and related schemas."""

    def test_token_creation(self):
        """Test Token model creation."""
        token = Token(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="bearer"
        )
        assert token.access_token == "access_token_value"
        assert token.refresh_token == "refresh_token_value"
        assert token.token_type == "bearer"

    def test_token_without_refresh_token(self):
        """Test Token without refresh token (admin login)."""
        token = Token(
            access_token="access_token_value",
            token_type="bearer"
        )
        assert token.access_token == "access_token_value"
        assert token.refresh_token is None
        assert token.token_type == "bearer"

    def test_token_default_token_type(self):
        """Test Token default token_type."""
        token = Token(
            access_token="access_token_value",
            refresh_token="refresh_token_value"
        )
        assert token.token_type == "bearer"

    def test_token_data_creation(self):
        """Test TokenData model creation."""
        token_data = TokenData(username="testuser")
        assert token_data.username == "testuser"

    def test_token_data_optional_username(self):
        """Test TokenData with optional username."""
        token_data = TokenData()
        assert token_data.username is None

    def test_token_refresh_request(self):
        """Test TokenRefreshRequest model."""
        refresh_request = TokenRefreshRequest(
            refresh_token="refresh_token_value"
        )
        assert refresh_request.refresh_token == "refresh_token_value"

    def test_token_refresh_request_required_field(self):
        """Test that refresh_token is required in TokenRefreshRequest."""
        with pytest.raises(ValidationError):
            TokenRefreshRequest()


class TestEnums:
    """Test enum models."""

    def test_user_type_enum_values(self):
        """Test UserType enum values."""
        assert UserType.ADMIN.value == "admin"
        assert UserType.VOLUNTEER.value == "volunteer"
        assert UserType.ASSOCIATION.value == "association"

    def test_user_type_enum_membership(self):
        """Test UserType enum membership."""
        assert "admin" in [ut.value for ut in UserType]
        assert "volunteer" in [ut.value for ut in UserType]
        assert "association" in [ut.value for ut in UserType]

    def test_user_type_from_string(self):
        """Test creating UserType from string."""
        assert UserType("admin") == UserType.ADMIN
        assert UserType("volunteer") == UserType.VOLUNTEER
        assert UserType("association") == UserType.ASSOCIATION

    def test_user_type_invalid_value(self):
        """Test that invalid UserType raises ValueError."""
        with pytest.raises(ValueError):
            UserType("invalid")

    def test_processing_status_enum_values(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.APPROVED.value == "approved"
        assert ProcessingStatus.REJECTED.value == "rejected"

    def test_processing_status_enum_membership(self):
        """Test ProcessingStatus enum membership."""
        statuses = [ps.value for ps in ProcessingStatus]
        assert "pending" in statuses
        assert "approved" in statuses
        assert "rejected" in statuses

    def test_processing_status_from_string(self):
        """Test creating ProcessingStatus from string."""
        assert ProcessingStatus("pending") == ProcessingStatus.PENDING
        assert ProcessingStatus("approved") == ProcessingStatus.APPROVED
        assert ProcessingStatus("rejected") == ProcessingStatus.REJECTED

    def test_enum_string_inheritance(self):
        """Test that enums inherit from str."""
        assert isinstance(UserType.ADMIN, str)
        assert isinstance(ProcessingStatus.PENDING, str)


class TestModelEdgeCases:
    """Test edge cases for models."""

    def test_user_with_empty_string_username(self):
        """Test user with empty string username."""
        # Pydantic allows empty strings by default
        user = UserBase(
            username="",
            email="test@example.com",
            user_type=UserType.VOLUNTEER
        )
        assert user.username == ""

    def test_user_with_very_long_email(self):
        """Test user with very long email."""
        long_email = "a" * 100 + "@" + "b" * 100 + ".com"
        user = UserBase(
            username="testuser",
            email=long_email,
            user_type=UserType.VOLUNTEER
        )
        assert len(user.email) > 200

    def test_admin_with_empty_names(self):
        """Test admin with empty name fields."""
        admin = AdminBase(
            first_name="",
            last_name="",
            email="test@example.com",
            username="testuser"
        )
        assert admin.first_name == ""
        assert admin.last_name == ""

    def test_token_with_empty_strings(self):
        """Test token with empty string values."""
        token = Token(
            access_token="",
            refresh_token="",
            token_type=""
        )
        assert token.access_token == ""
        assert token.refresh_token == ""
        assert token.token_type == ""

    def test_user_create_with_unicode_password(self):
        """Test UserCreate with unicode characters in password."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER,
            password="пароль123"  # Russian + numbers
        )
        assert user.password == "пароль123"

    def test_admin_with_unicode_names(self):
        """Test admin with unicode characters in names."""
        admin = AdminBase(
            first_name="José",
            last_name="Müller",
            email="jose@example.com",
            username="josemuller"
        )
        assert admin.first_name == "José"
        assert admin.last_name == "Müller"

    def test_user_update_all_fields(self):
        """Test UserUpdate with all fields set."""
        user_update = UserUpdate(
            email="new@example.com",
            user_type=UserType.ASSOCIATION,
            password="newpassword"
        )
        assert user_update.email == "new@example.com"
        assert user_update.user_type == UserType.ASSOCIATION
        assert user_update.password == "newpassword"

    def test_admin_update_all_fields(self):
        """Test AdminUpdate with all fields set."""
        admin_update = AdminUpdate(
            first_name="NewFirst",
            last_name="NewLast",
            email="new@example.com"
        )
        assert admin_update.first_name == "NewFirst"
        assert admin_update.last_name == "NewLast"
        assert admin_update.email == "new@example.com"

    def test_token_data_with_special_username(self):
        """Test TokenData with special characters in username."""
        token_data = TokenData(username="user@example.com")
        assert token_data.username == "user@example.com"

    def test_user_type_comparison(self):
        """Test UserType enum comparison."""
        assert UserType.ADMIN == UserType.ADMIN
        assert UserType.ADMIN != UserType.VOLUNTEER
        assert UserType.ADMIN == "admin"

    def test_processing_status_comparison(self):
        """Test ProcessingStatus enum comparison."""
        assert ProcessingStatus.PENDING == ProcessingStatus.PENDING
        assert ProcessingStatus.PENDING != ProcessingStatus.APPROVED
        assert ProcessingStatus.PENDING == "pending"


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_user_public_to_dict(self):
        """Test UserPublic serialization to dict."""
        user_public = UserPublic(
            username="testuser",
            email="test@example.com",
            user_type=UserType.VOLUNTEER,
            id_user=1,
            date_creation=datetime.now()
        )
        user_dict = user_public.model_dump()
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["id_user"] == 1

    def test_admin_public_to_dict(self):
        """Test AdminPublic serialization to dict."""
        admin_public = AdminPublic(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            username="johndoe",
            id_admin=1
        )
        admin_dict = admin_public.model_dump()
        assert admin_dict["first_name"] == "John"
        assert admin_dict["username"] == "johndoe"
        assert admin_dict["id_admin"] == 1

    def test_token_to_dict(self):
        """Test Token serialization to dict."""
        token = Token(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer"
        )
        token_dict = token.model_dump()
        assert token_dict["access_token"] == "access"
        assert token_dict["refresh_token"] == "refresh"
        assert token_dict["token_type"] == "bearer"

    def test_user_create_from_dict(self):
        """Test UserCreate deserialization from dict."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "user_type": "volunteer",
            "password": "password123"
        }
        user = UserCreate(**data)
        assert user.username == "testuser"
        assert user.password == "password123"

    def test_admin_create_from_dict(self):
        """Test AdminCreate deserialization from dict."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "username": "johndoe",
            "password": "password123"
        }
        admin = AdminCreate(**data)
        assert admin.first_name == "John"
        assert admin.password == "password123"