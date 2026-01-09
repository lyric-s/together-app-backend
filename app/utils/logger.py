import logging
import sys
import os
from types import FrameType
from loguru import logger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry._logs import set_logger_provider


class InterceptHandler(logging.Handler):
    """
    Redirects standard logging to Loguru.
    Includes a safety check to prevent infinite recursion with OTel.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # CRITICAL FIX: Ignore OTel internal logs to prevent recursion loops
        """
        Forward a standard logging.LogRecord to Loguru while avoiding OpenTelemetry recursion.

        Ignores any record whose logger name starts with "opentelemetry". Maps the record's logging level to a Loguru level when possible, determines the correct caller frame depth to preserve original callsite information, and emits the message to Loguru including any exception information from the record.

        Parameters:
            record (logging.LogRecord): The log record to be forwarded to Loguru.
        """
        if record.name.startswith("opentelemetry"):
            return

        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    Configure application logging to route Python's standard logging through Loguru and, when configured, export logs to OpenTelemetry (OTLP).

    This replaces the root logging handlers with an InterceptHandler, attaches InterceptHandler to common framework loggers (uvicorn, gunicorn, fastapi, sqlalchemy), and configures Loguru to write colorized, asynchronous logs to stderr. If the environment variable OTEL_EXPORTER_OTLP_ENDPOINT is set, also initializes an OpenTelemetry LoggerProvider and OTLPLogExporter (using OTEL_SERVICE_NAME, ENVIRONMENT, and OTEL_EXPORTER_OTLP_INSECURE) and attaches an OpenTelemetry logging handler to Loguru; failures during OTLP setup are printed to stderr but do not raise.

    Returns:
        logger: The configured Loguru logger object.
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    loggers_to_hijack = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy.engine",
    ]

    for name in loggers_to_hijack:
        log = logging.getLogger(name)
        log.handlers = []  # Remove Console handler
        log.propagate = False
        log.addHandler(InterceptHandler())  # Redirect to Loguru

    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> <level>{level}</level>: <cyan>[{name}:{line}]</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True,  # Async safety
    )

    # 3. CONFIGURE OPENTELEMETRY SINK
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        try:
            resource = Resource.create(
                {
                    "service.name": os.getenv("OTEL_SERVICE_NAME", "fastapi-app"),
                    "deployment.environment": os.getenv("ENVIRONMENT", "production"),
                }
            )

            logger_provider = LoggerProvider(resource=resource)
            set_logger_provider(logger_provider)

            insecure = (
                os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"
            )
            exporter = OTLPLogExporter(endpoint=endpoint, insecure=insecure)
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

            # Create standard OTel handler
            otel_handler = LoggingHandler(
                level=logging.INFO, logger_provider=logger_provider
            )
            logger.add(otel_handler, level="INFO", serialize=True)

            logger.info("Logging (Loguru Sink) Active.")

        except Exception as e:
            # Print to stderr directly if OTel fails, don't crash the app
            print(f"Log Setup Failed: {e}", file=sys.stderr)

    return logger
