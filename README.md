# 🚀 Together X FastAPI

A high-performance, containerized, and observable Python REST API built with **FastAPI**. This project emphasizes modern development practices, strict typing, security, and full-stack observability using **OpenTelemetry** and **SigNoz**.

## 🛠 Tech Stack

### Development Environment
* **Package Manager:** [uv](https://docs.astral.sh/uv/) (Fast Python package installer)
* **Pre-validation Hooks:** [Prek](https://prek.j178.dev/)
* **Linting & Formatting:** [Ruff](https://docs.astral.sh/ruff)
* **Type Checking:** [Pyrefly](https://pyrefly.org/) (Static Type Verification)

### Backend & Server
* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Server:** [Gunicorn](https://gunicorn.org/) with [Uvicorn](https://uvicorn.dev/) workers
* **Database:** PostgreSQL with [SQLModel](https://sqlmodel.tiangolo.com/) (ORM)
* **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
* **Security:** OAuth2 (JWT) & CORS Configuration

### Observability & Infrastructure
* **Instrumentation:** [OpenTelemetry](https://opentelemetry.io/)
* **Monitoring/Tracing:** [SigNoz](https://signoz.io/) (Self-hosted)
* **Containerization:** Docker & Docker Compose

---

## 📂 Project Structure

```text
.
├── app
│   ├── core         # Config, Security, Dependencies, Telemetry
│   ├── database     # DB connection (database.py)
│   ├── internal     # Admin/Internal routers
│   ├── models       # SQLModel tables and Pydantic schemas
│   ├── routers      # Public API endpoints
│   ├── services     # Business logic
│   ├── utils        # Utilities (logger.py, etc.)
│   └── main.py      # Application entrypoint
├── tests            # Unit and Integration tests
├── alembic          # Database migrations (Not yet implemented)
├── compose.yml      # Related Or Equivalent: Docker orchestration
├── pyproject.toml   # Project configuration
├── gunicorn_conf.py # Gunicorn configuration file
└── uv.lock          # Dependency lock file
```

---

## ⚡ Local Development Setup

### 1. Prerequisites
* **Docker** & **Docker Compose**
* **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. Installation
Clone the repository and install dependencies using `uv`:

```bash
git clone https://github.com/Lyric-s/together-app-backend
cd together-app-backend

# Create virtualenv
uv venv

# activate the .venv afterwards depending on your OS/Terminal for convenience

# Install dependencies
uv sync
```

### 3. Environment Configuration
Create a `.env` file based on the example (or strictly follow the `Settings` model in `app/core/config.py`).

```bash
cp .env.example .env
```

### 4. Database Migrations (Not yet implemented, you can skip this part)
Before running the app locally, ensure your database is running and apply the schema:

```bash
# Apply migrations
uv run alembic upgrade head
```

### 5. Run Locally
Start the API with hot-reload enabled:

```bash
uv run uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

---

## 🐋 Running the Full Stack (Docker)

To start the API, PostgreSQL Database, and the **SigNoz Observability Suite** together (SigNoz is currently only on the production servers):

```bash
docker compose up -d --build
```

### Services Overview
| Service | URL | Description |
| :--- | :--- | :--- |
| **API** | `http://localhost:8000` | The FastAPI Backend |
| **Swagger UI** | `http://localhost:8000/docs` | Interactive API Documentation |
| **SigNoz** | `http://localhost:3301` | Metrics, Traces, and Logs Dashboard (Not locally yet) |
| **PostgreSQL** | `localhost:5432` | Main Database |

---

## 📖 API Documentation

The API provides interactive documentation generated automatically from the codebase.

1.  **Swagger UI (`/docs`)**:
    * Navigate to `http://localhost:8000/docs`.
    * Use the **Authorize** button to log in.
    * **Note:** The login endpoint expects a `username` and `password` both present in the database.

2.  **ReDoc (`/redoc`)**:
    * Navigate to `http://localhost:8000/redoc`.
    * Useful for viewing the API specification in a clean document format : depends on one's tastes.

---

## ✅ Quality Assurance

We enforce code quality using strict blazingly fast linters and type checkers (written in Rust).

### Static Analysis
```bash
# Run Linter (Ruff)
uv run ruff check .

# Run Type Checker (Pyrefly)
uv run pyrefly
```

### Pre-Validation Hooks
We use `prek` hooks to validate code before committing.
```bash
# Run hooks manually
uv run prek run --all-files
```

### Tests
Run the unit and integration test suite:
```bash
uv run pytest
```

---

## 📊 Observability (SigNoz)

We use **OpenTelemetry** to instrument the application (only on production servers currently, the following can be skipped until the next part).

1.  Open SigNoz at `http://localhost:3301`.
2.  Create an admin account (first run only).
3.  Navigate to the **Traces** tab.
4.  Filter by service: `fastapi-app`.
5.  View:
    * Request Latency (P99, P95)
    * Database Query Performance
    * Error Rates and Stack Traces

---

## 🚀 Workflow (CI/CD)

The project includes a **GitHub Actions** workflow that:
1.  Installs `uv`.
2.  Runs `ruff` and `pyrefly` checks.
3.  Runs `pytest`.
4.  Runs `commitizen` to validate commits name on branch.

---

## 🤝 How to properly name commits

### `<prefix>: <JIRA-1> <commit message>`

`prefix` is **meant to be replaced** by one of the expected prefixes which can be found in the section below, it is **mandatory** to put one.

`JIRA-1` is an example **meant to be replaced** by the actual ticket name, in capital letters, related to the work being done on the branch. \
If the branch you are committing on is **not linked** to a JIRA ticket, just write the message; otherwise, you **must** include the ticket name.

`commit message` is **meant to be replaced** and must have **no capital letters**. It should be no more than a **short, but clear, sentence**.

## 📝 Expected prefixes

- `feat:` Introduces a **new feature**.
- `fix:` A **bug fix**.
- `build:` Changes that affect the **build system or external dependencies**.
- `chore:` Routine tasks that **don’t affect source or test code** (e.g., maintenance, cleanup).
- `ci:` Changes to **continuous integration configuration** (CI scripts, workflows).
- `docs:` Documentation-only changes.
- `style:` Code changes that **don’t affect meaning** (formatting, whitespace, semicolons).
- `refactor:` Code changes that **neither fix bugs nor add features** (structural improvements).
- `perf:` Code changes that **improve performance**.
- `test:` Adding or modifying **tests**.
- `revert:` Reverts a previous commit.

## 📢 Breaking Changes

### **BREAKING CHANGE:** (footer)
A footer indicating a **breaking API change** → major SemVer bump.

### **! after type**
Alternative breaking-change notation:
Example: `feat!: change API behavior`

[source: conventional commits organization website](https://www.conventionalcommits.org/en/v1.0.0/#specification)
