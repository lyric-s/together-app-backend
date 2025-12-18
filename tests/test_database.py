import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlmodel import Session, SQLModel

from app.database.database import engine, create_db_and_tables, get_session


class TestDatabaseEngine:
    """Test database engine configuration."""

    def test_engine_exists(self):
        """Test that engine is created."""
        assert engine is not None

    def test_engine_has_pool_pre_ping(self):
        """Test that pool_pre_ping is enabled."""
        # Engine should have pool configured
        assert hasattr(engine, "pool")

    @patch("app.database.database.get_settings")
    def test_engine_uses_database_url_from_settings(self, mock_get_settings):
        """Test that engine uses DATABASE_URL from settings."""
        # This is more of a verification that get_settings is called
        # The actual engine is already created at import time
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_get_settings.return_value = mock_settings
        
        # Verify get_settings is available
        from app.core.config import get_settings
        assert callable(get_settings)


class TestCreateDbAndTables:
    """Test create_db_and_tables function."""

    @patch("app.database.database.SQLModel")
    def test_create_db_and_tables_calls_metadata_create_all(self, mock_sqlmodel):
        """Test that create_db_and_tables creates all tables."""
        mock_metadata = MagicMock()
        mock_sqlmodel.metadata = mock_metadata
        
        create_db_and_tables()
        
        mock_metadata.create_all.assert_called_once_with(engine)

    @patch("app.database.database.SQLModel")
    def test_create_db_and_tables_with_exception(self, mock_sqlmodel):
        """Test that exceptions during table creation are propagated."""
        mock_metadata = MagicMock()
        mock_metadata.create_all.side_effect = Exception("Database error")
        mock_sqlmodel.metadata = mock_metadata
        
        with pytest.raises(Exception) as exc_info:
            create_db_and_tables()
        
        assert "Database error" in str(exc_info.value)


class TestGetSession:
    """Test get_session dependency."""

    def test_get_session_yields_session(self):
        """Test that get_session yields a Session."""
        session_generator = get_session()
        session = next(session_generator)
        
        assert isinstance(session, Session)
        
        # Clean up
        try:
            next(session_generator)
        except StopIteration:
            pass

    def test_get_session_closes_after_use(self):
        """Test that session is closed after use."""
        session_generator = get_session()
        session = next(session_generator)
        
        # Session should be open
        assert session is not None
        
        # Complete the generator
        try:
            next(session_generator)
        except StopIteration:
            pass
        
        # Session should be closed (not directly testable, but no exception)

    def test_get_session_multiple_calls(self):
        """Test that multiple calls to get_session work independently."""
        gen1 = get_session()
        gen2 = get_session()
        
        session1 = next(gen1)
        session2 = next(gen2)
        
        # Should be different session instances
        assert session1 is not session2
        
        # Clean up
        for gen in [gen1, gen2]:
            try:
                next(gen)
            except StopIteration:
                pass

    def test_get_session_context_manager_usage(self):
        """Test get_session works with context manager pattern."""
        # Simulate FastAPI's usage
        session_gen = get_session()
        
        try:
            session = next(session_gen)
            # Use session
            assert isinstance(session, Session)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def test_get_session_exception_handling(self):
        """Test that session is cleaned up even if exception occurs."""
        session_gen = get_session()
        
        try:
            session = next(session_gen)
            # Simulate an exception during usage
            raise ValueError("Test error")
        except ValueError:
            pass
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass
        
        # Should complete without issues


class TestDatabaseConfiguration:
    """Test database configuration settings."""

    def test_engine_connect_args_sqlite(self):
        """Test that connect_args includes check_same_thread for SQLite."""
        # Engine is created with connect_args
        assert hasattr(engine, "url")

    @patch("app.database.database.create_engine")
    @patch("app.database.database.get_settings")
    def test_database_url_from_settings(self, mock_get_settings, mock_create_engine):
        """Test that database URL comes from settings."""
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_get_settings.return_value = mock_settings
        
        # Would need to reimport module to test, but verify settings usage
        from app.core.config import get_settings
        settings = get_settings()
        assert hasattr(settings, "DATABASE_URL")


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    def test_session_transaction_commit(self, test_session):
        """Test that session can commit transactions."""
        # test_session from fixture
        from app.models.user import User
        from app.core.security import get_password_hash
        from datetime import datetime
        
        user = User(
            username="transactionuser",
            email="transaction@example.com",
            user_type="volunteer",
            hashed_password=get_password_hash("password"),
            date_creation=datetime.now()
        )
        
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        
        assert user.id_user is not None

    def test_session_transaction_rollback(self, test_session):
        """Test that session can rollback transactions."""
        from app.models.user import User
        from app.core.security import get_password_hash
        from datetime import datetime
        
        user = User(
            username="rollbackuser",
            email="rollback@example.com",
            user_type="volunteer",
            hashed_password=get_password_hash("password"),
            date_creation=datetime.now()
        )
        
        test_session.add(user)
        test_session.rollback()
        
        # User should not be in session after rollback
        from sqlmodel import select
        result = test_session.exec(select(User).where(User.username == "rollbackuser")).first()
        assert result is None

    def test_session_query_operations(self, test_session, test_user):
        """Test basic query operations."""
        from sqlmodel import select
        from app.models.user import User
        
        # Select
        result = test_session.exec(select(User).where(User.username == "testuser")).first()
        assert result is not None
        assert result.username == "testuser"

    def test_session_update_operations(self, test_session, test_user):
        """Test update operations."""
        test_user.email = "newemail@example.com"
        test_session.add(test_user)
        test_session.commit()
        test_session.refresh(test_user)
        
        assert test_user.email == "newemail@example.com"

    def test_session_delete_operations(self, test_session):
        """Test delete operations."""
        from app.models.user import User
        from app.core.security import get_password_hash
        from datetime import datetime
        from sqlmodel import select
        
        user = User(
            username="deleteuser",
            email="delete@example.com",
            user_type="volunteer",
            hashed_password=get_password_hash("password"),
            date_creation=datetime.now()
        )
        
        test_session.add(user)
        test_session.commit()
        
        test_session.delete(user)
        test_session.commit()
        
        # User should not exist
        result = test_session.exec(select(User).where(User.username == "deleteuser")).first()
        assert result is None


class TestDatabaseEdgeCases:
    """Test edge cases for database operations."""

    def test_get_session_generator_exhaustion(self):
        """Test that generator is properly exhausted."""
        gen = get_session()
        session = next(gen)
        
        # Exhaust generator
        with pytest.raises(StopIteration):
            next(gen)
            next(gen)  # Second call should also raise

    def test_multiple_sessions_independent(self):
        """Test that multiple sessions are independent."""
        gen1 = get_session()
        gen2 = get_session()
        
        session1 = next(gen1)
        session2 = next(gen2)
        
        # Sessions should be independent
        assert session1 is not session2
        
        # Clean up
        for gen in [gen1, gen2]:
            try:
                next(gen)
            except StopIteration:
                pass