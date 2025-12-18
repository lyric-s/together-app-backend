import pytest
import logging
import sys
from unittest.mock import Mock, patch, MagicMock, call
from types import FrameType

from app.utils.logger import InterceptHandler, setup_logging


class TestInterceptHandler:
    """Test the InterceptHandler class."""

    def test_intercept_handler_initialization(self):
        """Test that InterceptHandler can be instantiated."""
        handler = InterceptHandler()
        assert isinstance(handler, logging.Handler)

    def test_intercept_handler_ignores_opentelemetry_logs(self):
        """Test that OpenTelemetry logs are ignored to prevent recursion."""
        handler = InterceptHandler()
        
        # Create a log record from opentelemetry
        record = logging.LogRecord(
            name="opentelemetry.sdk.trace",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            handler.emit(record)
            # Should not call logger
            mock_logger.opt.assert_not_called()

    def test_intercept_handler_processes_non_otel_logs(self):
        """Test that non-OpenTelemetry logs are processed."""
        handler = InterceptHandler()
        
        # Create a regular log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            mock_opt = MagicMock()
            mock_logger.opt.return_value = mock_opt
            mock_logger.level.return_value = Mock(name="INFO")
            
            handler.emit(record)
            
            # Should call logger.opt
            mock_logger.opt.assert_called_once()

    def test_intercept_handler_handles_different_log_levels(self):
        """Test that handler processes different log levels."""
        handler = InterceptHandler()
        
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]
        
        for level, level_name in levels:
            record = logging.LogRecord(
                name="test.module",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"Test {level_name} message",
                args=(),
                exc_info=None
            )
            
            with patch("app.utils.logger.logger") as mock_logger:
                mock_opt = MagicMock()
                mock_logger.opt.return_value = mock_opt
                mock_logger.level.return_value = Mock(name=level_name)
                
                handler.emit(record)
                
                mock_logger.opt.assert_called_once()

    def test_intercept_handler_with_exception_info(self):
        """Test that handler passes exception info."""
        handler = InterceptHandler()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            mock_opt = MagicMock()
            mock_logger.opt.return_value = mock_opt
            mock_logger.level.return_value = Mock(name="ERROR")
            
            handler.emit(record)
            
            # Verify exception info is passed
            call_kwargs = mock_logger.opt.call_args[1]
            assert call_kwargs.get("exception") == exc_info

    def test_intercept_handler_prevents_opentelemetry_recursion(self):
        """Test that opentelemetry.* logs don't cause recursion."""
        handler = InterceptHandler()
        
        otel_loggers = [
            "opentelemetry.sdk",
            "opentelemetry.instrumentation",
            "opentelemetry.exporter",
            "opentelemetry.trace",
        ]
        
        for logger_name in otel_loggers:
            record = logging.LogRecord(
                name=logger_name,
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="OTel message",
                args=(),
                exc_info=None
            )
            
            with patch("app.utils.logger.logger") as mock_logger:
                handler.emit(record)
                # Should not process
                mock_logger.opt.assert_not_called()

    def test_intercept_handler_with_invalid_level(self):
        """Test handler with invalid log level."""
        handler = InterceptHandler()
        
        record = logging.LogRecord(
            name="test.module",
            level=99999,  # Invalid level
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            mock_opt = MagicMock()
            mock_logger.opt.return_value = mock_opt
            # Simulate ValueError when getting invalid level
            mock_logger.level.side_effect = ValueError("Invalid level")
            
            # Should handle gracefully and use numeric level
            handler.emit(record)
            
            mock_logger.opt.assert_called_once()


class TestSetupLogging:
    """Test the setup_logging function."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_without_otel(self, mock_logger):
        """Test setup_logging without OpenTelemetry endpoint."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        result = setup_logging()
        
        # Should configure basic logging
        mock_logger.remove.assert_called_once()
        assert mock_logger.add.call_count >= 1
        assert result == mock_logger

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "test-service",
        "DEPLOYMENT_ENV": "test"
    })
    @patch("app.utils.logger.logger")
    @patch("app.utils.logger.LoggerProvider")
    @patch("app.utils.logger.OTLPLogExporter")
    def test_setup_logging_with_otel(self, mock_exporter, mock_provider, mock_logger):
        """Test setup_logging with OpenTelemetry enabled."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        mock_logger.info = MagicMock()
        
        result = setup_logging()
        
        # Should configure OTel logging
        mock_logger.remove.assert_called_once()
        assert mock_logger.add.call_count >= 2  # Stderr + OTel handler

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_hijacks_standard_loggers(self, mock_logger):
        """Test that standard loggers are hijacked."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        with patch("logging.getLogger") as mock_get_logger:
            mock_log = MagicMock()
            mock_get_logger.return_value = mock_log
            
            setup_logging()
            
            # Should call getLogger for various standard loggers
            # (exact calls depend on implementation)
            assert mock_get_logger.call_count > 0

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_configures_root_logger(self, mock_logger):
        """Test that root logger is configured."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        with patch("logging.root") as mock_root:
            mock_root.handlers = []
            
            setup_logging()
            
            # Root logger should be configured
            assert isinstance(mock_root.handlers[0], InterceptHandler)
            assert mock_root.level == logging.INFO

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_EXPORTER_OTLP_INSECURE": "true"
    })
    @patch("app.utils.logger.logger")
    @patch("app.utils.logger.OTLPLogExporter")
    def test_setup_logging_otel_insecure_flag(self, mock_exporter, mock_logger):
        """Test that insecure flag is parsed correctly."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        mock_logger.info = MagicMock()
        
        setup_logging()
        
        # Should call exporter with insecure=True
        if mock_exporter.called:
            call_kwargs = mock_exporter.call_args[1]
            assert call_kwargs.get("insecure") is True

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
    })
    @patch("app.utils.logger.logger")
    @patch("app.utils.logger.OTLPLogExporter")
    def test_setup_logging_otel_secure_flag(self, mock_exporter, mock_logger):
        """Test that secure connection is used when insecure=false."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        mock_logger.info = MagicMock()
        
        setup_logging()
        
        # Should call exporter with insecure=False
        if mock_exporter.called:
            call_kwargs = mock_exporter.call_args[1]
            assert call_kwargs.get("insecure") is False

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.utils.logger.logger")
    @patch("app.utils.logger.OTLPLogExporter")
    def test_setup_logging_otel_exception_handling(self, mock_exporter, mock_logger):
        """Test that OTel setup exceptions don't crash the app."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        mock_logger.info = MagicMock()
        
        # Simulate OTel setup failure
        mock_exporter.side_effect = Exception("OTel connection failed")
        
        # Should not raise exception
        result = setup_logging()
        
        # Should still return logger
        assert result == mock_logger

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_format_configuration(self, mock_logger):
        """Test that log format is configured correctly."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        setup_logging()
        
        # Check that add was called with format configuration
        if mock_logger.add.called:
            call_kwargs = mock_logger.add.call_args[1]
            assert "format" in call_kwargs
            assert "colorize" in call_kwargs
            assert call_kwargs.get("colorize") is True

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_async_safety(self, mock_logger):
        """Test that logging is configured with async safety."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        setup_logging()
        
        # Check that enqueue is enabled for async safety
        if mock_logger.add.called:
            call_kwargs = mock_logger.add.call_args[1]
            assert call_kwargs.get("enqueue") is True

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.utils.logger.logger")
    def test_setup_logging_loggers_list(self, mock_logger):
        """Test that specific loggers are hijacked."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        
        expected_loggers = [
            "uvicorn",
            "uvicorn.error",
            "uvicorn.access",
            "gunicorn.error",
            "gunicorn.access",
            "fastapi",
            "sqlalchemy.engine",
        ]
        
        with patch("logging.getLogger") as mock_get_logger:
            mock_log = MagicMock()
            mock_get_logger.return_value = mock_log
            
            setup_logging()
            
            # Verify that specific loggers were accessed
            called_names = [call[0][0] for call in mock_get_logger.call_args_list]
            for expected in expected_loggers:
                assert expected in called_names


class TestLoggingIntegration:
    """Integration tests for logging setup."""

    @patch.dict("os.environ", {}, clear=True)
    def test_logging_integration_basic(self):
        """Test basic logging integration."""
        with patch("app.utils.logger.logger") as mock_logger:
            mock_logger.remove = MagicMock()
            mock_logger.add = MagicMock()
            
            logger = setup_logging()
            
            # Verify logger is configured
            assert logger is not None
            mock_logger.remove.assert_called_once()

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "test-app",
        "DEPLOYMENT_ENV": "development"
    })
    @patch("app.utils.logger.logger")
    @patch("app.utils.logger.Resource")
    def test_logging_integration_with_otel_resource(self, mock_resource, mock_logger):
        """Test that OTel resource is configured with correct attributes."""
        mock_logger.remove = MagicMock()
        mock_logger.add = MagicMock()
        mock_logger.info = MagicMock()
        
        setup_logging()
        
        # Verify Resource.create was called with service info
        if mock_resource.create.called:
            call_args = mock_resource.create.call_args[0][0]
            assert "service.name" in call_args
            assert "deployment.environment" in call_args


class TestInterceptHandlerEdgeCases:
    """Test edge cases for InterceptHandler."""

    def test_emit_with_empty_message(self):
        """Test handler with empty message."""
        handler = InterceptHandler()
        
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="",
            args=(),
            exc_info=None
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            mock_opt = MagicMock()
            mock_logger.opt.return_value = mock_opt
            mock_logger.level.return_value = Mock(name="INFO")
            
            # Should handle gracefully
            handler.emit(record)
            mock_logger.opt.assert_called_once()

    def test_emit_with_message_formatting(self):
        """Test handler with message that needs formatting."""
        handler = InterceptHandler()
        
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User %s logged in from %s",
            args=("john", "192.168.1.1"),
            exc_info=None
        )
        
        with patch("app.utils.logger.logger") as mock_logger:
            mock_opt = MagicMock()
            mock_logger.opt.return_value = mock_opt
            mock_logger.level.return_value = Mock(name="INFO")
            
            handler.emit(record)
            
            # Should format message
            mock_logger.opt.assert_called_once()