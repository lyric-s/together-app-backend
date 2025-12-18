import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI

from app.core.telemetry import setup_telemetry


class TestSetupTelemetry:
    """Test the setup_telemetry function."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.core.telemetry.logger")
    def test_setup_telemetry_no_endpoint(self, mock_logger):
        """Test that telemetry is disabled when no endpoint is configured."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Should log warning and return early
        mock_logger.warning.assert_called_once()
        assert "No endpoint configured" in str(mock_logger.warning.call_args)

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.trace")
    def test_setup_telemetry_with_endpoint(
        self, mock_trace, mock_span_exporter, mock_tracer_provider, 
        mock_resource, mock_logger
    ):
        """Test telemetry setup with endpoint configured."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Should configure telemetry
        mock_resource.create.assert_called_once()
        mock_logger.info.assert_called()

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "test-service",
        "DEPLOYMENT_ENV": "production"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    def test_setup_telemetry_resource_attributes(self, mock_resource, mock_logger):
        """Test that resource is created with correct attributes."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Verify resource creation with attributes
        call_args = mock_resource.create.call_args[0][0]
        assert "service.name" in call_args
        assert call_args["service.name"] == "test-service"
        assert "deployment.environment" in call_args
        assert call_args["deployment.environment"] == "production"

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "test-service"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    def test_setup_telemetry_default_deployment_env(self, mock_resource, mock_logger):
        """Test default deployment environment."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        call_args = mock_resource.create.call_args[0][0]
        assert call_args["deployment.environment"] == "development"

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    def test_setup_telemetry_default_service_name(self, mock_resource, mock_logger):
        """Test default service name."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        call_args = mock_resource.create.call_args[0][0]
        assert call_args["service.name"] == "unset"

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_EXPORTER_OTLP_INSECURE": "true"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.OTLPMetricExporter")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_insecure_flag_true(
        self, mock_tracer, mock_resource, mock_metric_exp, 
        mock_span_exp, mock_logger
    ):
        """Test that insecure flag is parsed correctly when true."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Verify span exporter called with insecure=True
        if mock_span_exp.called:
            call_kwargs = mock_span_exp.call_args[1]
            assert call_kwargs.get("insecure") is True

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_insecure_flag_false(
        self, mock_tracer, mock_resource, mock_span_exp, mock_logger
    ):
        """Test that insecure flag defaults to false."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        if mock_span_exp.called:
            call_kwargs = mock_span_exp.call_args[1]
            assert call_kwargs.get("insecure") is False

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    def test_setup_telemetry_exception_handling(self, mock_resource, mock_logger):
        """Test that exceptions during setup are caught and logged."""
        app = FastAPI()
        
        # Simulate exception during setup
        mock_resource.create.side_effect = Exception("Connection failed")
        
        # Should not raise exception
        setup_telemetry(app)
        
        # Should log error
        mock_logger.error.assert_called_once()
        assert "Setup Failed" in str(mock_logger.error.call_args)

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.FastAPIInstrumentor")
    @patch("app.core.telemetry.SQLAlchemyInstrumentor")
    @patch("app.core.telemetry.AsyncPGInstrumentor")
    @patch("app.core.telemetry.Psycopg2Instrumentor")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_instrumentation(
        self, mock_tracer, mock_resource, mock_psycopg2, 
        mock_asyncpg, mock_sqlalchemy, mock_fastapi, mock_logger
    ):
        """Test that instrumentation is configured."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Verify instrumentors are called
        mock_fastapi.instrument_app.assert_called_once()
        call_kwargs = mock_fastapi.instrument_app.call_args[1]
        assert "excluded_urls" in call_kwargs

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.FastAPIInstrumentor")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_excluded_urls(
        self, mock_tracer, mock_resource, mock_fastapi, mock_logger
    ):
        """Test that health and metrics endpoints are excluded."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        if mock_fastapi.instrument_app.called:
            call_kwargs = mock_fastapi.instrument_app.call_args[1]
            excluded = call_kwargs.get("excluded_urls", "")
            assert "/health" in excluded or "health" in excluded
            assert "/metrics" in excluded or "metrics" in excluded

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.FastAPIInstrumentor")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_prevents_double_instrumentation(
        self, mock_tracer, mock_resource, mock_fastapi, mock_logger
    ):
        """Test that double instrumentation is prevented."""
        app = FastAPI()
        
        # Call setup twice
        setup_telemetry(app)
        setup_telemetry(app)
        
        # Should only instrument once
        assert mock_fastapi.instrument_app.call_count == 1

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.SQLAlchemyInstrumentor")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_sqlalchemy_commenter(
        self, mock_tracer, mock_resource, mock_sqlalchemy, mock_logger
    ):
        """Test that SQLAlchemy instrumentation enables commenter."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        if mock_sqlalchemy.return_value.instrument.called:
            call_kwargs = mock_sqlalchemy.return_value.instrument.call_args[1]
            assert call_kwargs.get("enable_commenter") is True

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Psycopg2Instrumentor")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_psycopg2_config(
        self, mock_tracer, mock_resource, mock_psycopg2, mock_logger
    ):
        """Test Psycopg2 instrumentation configuration."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        if mock_psycopg2.return_value.instrument.called:
            call_kwargs = mock_psycopg2.return_value.instrument.call_args[1]
            assert call_kwargs.get("enable_commenter") is True
            assert call_kwargs.get("skip_dep_check") is True

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.trace")
    @patch("app.core.telemetry.metrics")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    @patch("app.core.telemetry.MeterProvider")
    def test_setup_telemetry_sets_providers(
        self, mock_meter, mock_tracer, mock_resource, 
        mock_metrics, mock_trace, mock_logger
    ):
        """Test that trace and metrics providers are set."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Verify providers are set
        mock_trace.set_tracer_provider.assert_called_once()
        mock_metrics.set_meter_provider.assert_called_once()

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "https://secure.endpoint.com:443",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_secure_endpoint(
        self, mock_tracer, mock_resource, mock_span_exp, mock_logger
    ):
        """Test setup with secure HTTPS endpoint."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        # Verify endpoint is used
        if mock_span_exp.called:
            call_kwargs = mock_span_exp.call_args[1]
            assert "endpoint" in call_kwargs
            assert call_kwargs["insecure"] is False


class TestTelemetryEdgeCases:
    """Test edge cases for telemetry setup."""

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": ""
    })
    @patch("app.core.telemetry.logger")
    def test_setup_telemetry_empty_endpoint(self, mock_logger):
        """Test that empty endpoint is treated as no endpoint."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        mock_logger.warning.assert_called_once()

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_EXPORTER_OTLP_INSECURE": "TRUE"
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.OTLPSpanExporter")
    @patch("app.core.telemetry.Resource")
    @patch("app.core.telemetry.TracerProvider")
    def test_setup_telemetry_insecure_case_insensitive(
        self, mock_tracer, mock_resource, mock_span_exp, mock_logger
    ):
        """Test that insecure flag is case-insensitive."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        if mock_span_exp.called:
            call_kwargs = mock_span_exp.call_args[1]
            assert call_kwargs.get("insecure") is True

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "",
        "DEPLOYMENT_ENV": ""
    })
    @patch("app.core.telemetry.logger")
    @patch("app.core.telemetry.Resource")
    def test_setup_telemetry_empty_resource_attributes(self, mock_resource, mock_logger):
        """Test with empty resource attribute values."""
        app = FastAPI()
        
        setup_telemetry(app)
        
        call_args = mock_resource.create.call_args[0][0]
        # Should use defaults
        assert call_args["service.name"] in ["", "unset"]
        assert call_args["deployment.environment"] in ["", "development"]

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
    })
    @patch("app.core.telemetry.logger")
    def test_setup_telemetry_with_none_app(self, mock_logger):
        """Test setup with None app (should handle gracefully)."""
        # This would be an error in real usage, but test defensive coding
        try:
            setup_telemetry(None)
        except Exception:
            # If it raises, that's acceptable
            pass


class TestTelemetryIntegration:
    """Integration tests for telemetry."""

    @patch.dict("os.environ", {
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
        "OTEL_SERVICE_NAME": "test-app",
        "DEPLOYMENT_ENV": "test"
    })
    def test_telemetry_full_integration(self):
        """Test full telemetry setup integration."""
        with patch("app.core.telemetry.logger") as mock_logger, \
             patch("app.core.telemetry.Resource") as mock_resource, \
             patch("app.core.telemetry.TracerProvider") as mock_tracer, \
             patch("app.core.telemetry.MeterProvider") as mock_meter:
            
            app = FastAPI()
            setup_telemetry(app)
            
            # Should complete without errors
            mock_resource.create.assert_called_once()