# Together App Backend

## Project Overview
**Together** is a REST API for a volunteer coordination platform. It connects non-profit organizations with volunteers. This backend is built with FastAPI and demonstrates modern Python development practices, including full-stack observability, containerization, and strict code quality standards.

## Tech Stack
*   **Language:** Python 3.12+
*   **Web Framework:** FastAPI
*   **Database:** PostgreSQL 17.6
*   **ORM:** SQLModel (Pydantic + SQLAlchemy)
*   **Migrations:** Alembic
*   **Package Manager:** uv
*   **Containerization:** Docker, Docker Compose
*   **Observability:** OpenTelemetry (traces, metrics, logs), SigNoz

## Key Directories
*   `app/`: Main application source code.
    *   `core/`: Configuration, security, dependencies.
    *   `models/`: SQLModel database tables and Pydantic schemas.
    *   `routers/`: API endpoints organized by feature.
    *   `services/`: Business logic.
*   `alembic/`: Database migration scripts.
*   `tests/`: Unit and integration tests (`pytest`).
*   `.github/workflows/`: CI/CD pipelines.

## Development Workflow

### Prerequisites
*   Python 3.12+
*   [uv](https://docs.astral.sh/uv/) (Package Manager)
*   Docker & Docker Compose

### Setup & Installation
1.  **Clone & Enter:**
    ```bash
    git clone <repo_url>
    cd together-app-backend
    ```
2.  **Install Dependencies:**
    ```bash
    uv sync
    ```
3.  **Environment Variables:**
    ```bash
    cp .env.example .env
    # Edit .env with your local config
    ```

### Running the Application

**Option A: Local Development (requires external DB)**
```bash
# Run migrations
uv run alembic upgrade head

# Start Server
uv run fastapi dev app/main.py
```
The API will be available at `http://127.0.0.1:8000`.

**Option B: Docker (All-in-one)**
```bash
docker compose up -d --build
```
This spins up the API and a PostgreSQL database.

### Common Commands

*   **Run Tests:** `uv run pytest`
*   **Linting:** `uv run ruff check`
*   **Formatting:** `uv run ruff format`
*   **Type Checking:** `uv run pyrefly check --summarize-errors`
*   **Migrations:**
    *   Create: `uv run alembic revision --autogenerate -m "message"`
    *   Apply: `uv run alembic upgrade head`

## Conventions
*   **Commits:** Follow [Conventional Commits](https://www.conventionalcommits.org/). Use `commitizen` if needed.
*   **Code Style:** Strictly enforced by `ruff`. Run `uv run prek run --all-files` to validate before committing.
*   **Architecture:** Follows a layered architecture: `Router` -> `Service` -> `CRUD/Model`. Keep business logic out of routers.
