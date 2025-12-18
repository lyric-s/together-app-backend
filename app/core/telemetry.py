import os
from fastapi import FastAPI
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from loguru import logger


def setup_telemetry(app: FastAPI):
    """
    Initialize OpenTelemetry tracing and metrics when an OTLP endpoint is configured.

    Creates and registers tracer and meter providers using OTLP exporters configured via environment variables (OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME, ENVIRONMENT, OTEL_EXPORTER_OTLP_INSECURE), and instruments the provided FastAPI app plus SQLAlchemy and Psycopg2 once. If no endpoint is configured, telemetry is left disabled; setup failures are logged but not raised.

    Parameters:
        app (FastAPI): FastAPI application to instrument (excludes /health and /metrics).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.warning("No endpoint configured. Telemetry disabled.")
        return
    try:
        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", "unset"),
                "deployment.environment": os.getenv("ENVIRONMENT", "unexpected"),
            }
        )

        insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"

        tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint, insecure=insecure)
        )
        meter_provider = MeterProvider(
            resource=resource, metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(meter_provider)

        # Track instrumentation state to prevent double instrumentation
        if not hasattr(setup_telemetry, "_instrumented"):
            FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
            SQLAlchemyInstrumentor().instrument(enable_commenter=True)  # type: ignore
            Psycopg2Instrumentor().instrument(  # type: ignore
                enable_commenter=True, skip_dep_check=True
            )
            setup_telemetry._instrumented = True  # type: ignore

        logger.info("Traces & Metrics Active.")

    except Exception as e:
        logger.error(f"Traces & Metrics Setup Failed: {e}")
