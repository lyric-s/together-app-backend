# Together X FastAPI Gemini Agent Context

This document provides a comprehensive overview of the Together X FastAPI project, intended to be used as instructional context for the Gemini agent.

## Project Overview

This is a Python REST API built with FastAPI, using SQLModel as the ORM and PostgreSQL as the database. The project is containerized with Docker and uses `uv` for package management. It emphasizes modern development practices with strict typing, security, and observability using OpenTelemetry.

## Building and Running

### Local Development (uv)

1.  **Install dependencies:**
    ```bash
    uv sync
    ```
2.  **Run the application:**
    ```bash
    uv run uvicorn app.main:app --reload
    ```

### Docker

1.  **Build and run the services:**
    ```bash
    docker compose up -d --build
    ```

## Testing

Run the test suite with:

```bash
uv run pytest
```

## Development Conventions

*   **Linting & Formatting:** The project uses `ruff` for linting and formatting. Run it with:
    ```bash
    uv run ruff check .
    ```
*   **Type Checking:** `pyrefly` is used for static type checking. Run it with:
    ```bash
    uv run pyrefly
    ```
*   **Commit Messages:** The project follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. Commits are validated using `commitizen`.

## Project Structure

The project follows a modular structure, with the main application logic in the `app` directory. Key subdirectories include:

*   `core`: Configuration, security, dependencies, and telemetry.
*   `database`: Database connection and session management.
*   `models`: SQLModel tables and Pydantic schemas.
*   `routers`: API endpoints.
*   `services`: Business logic.
*   `utils`: Utility functions.
