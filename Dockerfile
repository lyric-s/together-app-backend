# STAGE 1: Builder

# We use this stage to compile and install everything into the virtual environment
# So that we get a small image with only the necessary
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-dev

# STAGE 2: Runner (Production)
FROM python:3.12-slim

# Install dos2unix to fix line endings from Windows development environment
RUN apt-get update && apt-get install -y --no-install-recommends dos2unix && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser
WORKDIR /app
USER appuser

# Copy the FULLY HYDRATED venv from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
# Copy app code
COPY --chown=appuser:appuser . .

# Fix line endings and make prestart.sh executable
RUN dos2unix scripts/prestart.sh && chmod +x scripts/prestart.sh

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["./scripts/prestart.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--forwarded-allow-ips='*'"]