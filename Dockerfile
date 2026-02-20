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

RUN useradd -m -u 1000 appuser
# Création du dossier de cache et attribution des droits à appuser
RUN mkdir -p /home/appuser/.cache/huggingface && chown -R appuser:appuser /home/appuser/.cache

WORKDIR /app
USER appuser

# Copy the FULLY HYDRATED venv from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
# Copy app code
COPY --chown=appuser:appuser . .

# Make prestart script executable
RUN chmod +x scripts/prestart.sh

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["./scripts/prestart.sh"]
CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--forwarded-allow-ips='*'"]
