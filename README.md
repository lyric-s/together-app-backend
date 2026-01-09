# 🚀 Together - FastAPI Backend

A production-ready, fully observable REST API built with **FastAPI**, demonstrating modern Python development practices, containerization, and full-stack observability.

> [!IMPORTANT]
> **Academic Project**: Created at **IUT Paris - Rives de Seine** (University of Paris) as part of an academic curriculum. While "Together" is a conceptual platform designed for educational purposes, it demonstrates production-ready backend API development with modern software engineering practices, DevOps workflows, and full-stack observability. This repository serves as both a learning resource and a reusable template for building scalable FastAPI applications.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.122+-green.svg)](https://fastapi.tiangolo.com/)
[![codecov](https://codecov.io/gh/lyric-s/together-app-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/lyric-s/together-app-backend)
[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/lyric-s/together-app-backend)

## 📑 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Setup](#docker-setup)
- [Frontend Development Setup](#-frontend-development-setup)
- [API Documentation](#-api-documentation)
- [Quality Assurance](#-quality-assurance)
- [Observability](#-observability)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [Using as a Template](#-using-as-a-template)
- [Project Links](#-project-links)
- [Infrastructure & Architecture](#️-infrastructure--architecture)
- [License](#-license)
- [Academic Context](#-academic-context)

---

> [!NOTE]
> **About Together**: A platform connecting non-profit organizations with volunteers. Associations can showcase their missions while volunteers discover opportunities matching their skills and interests. Unlike similar platforms like [jeveuxaider.gouv.fr](https://www.jeveuxaider.gouv.fr/), Together is **open-source** and designed for international adaptability.

## ✨ Features

### Core Functionality

- ✅ **RESTful API** with [FastAPI](https://fastapi.tiangolo.com/) and automatic [OpenAPI](https://www.openapis.org/) documentation
- ✅ **Authentication & Authorization** with [OAuth2](https://oauth.net/2/) ([JWT](https://jwt.io/) tokens)
- ✅ **Database Management** using [SQLModel](https://sqlmodel.tiangolo.com/) ORM with [PostgreSQL](https://www.postgresql.org/)
- ✅ **Database Migrations** with [Alembic](https://alembic.sqlalchemy.org/)
- ✅ **File Storage** integration with [MinIO](https://min.io/)/S3-compatible services
- ✅ **CORS Configuration** for secure cross-origin requests

### Development Experience

- ✅ **Fast Package Management** with [uv](https://docs.astral.sh/uv/)
- ✅ **Code Quality** enforced by [Ruff](https://docs.astral.sh/ruff) (linting & formatting)
- ✅ **Static Type Checking** with [Pyrefly](https://pyrefly.org/)
- ✅ **Pre-commit Hooks** using [Prek](https://prek.j178.dev/)
- ✅ **Conventional Commits** with [Commitizen](https://commitizen-tools.github.io/commitizen/)
- ✅ **Automated Testing** with [pytest](https://pytest.org/)
- ✅ **Code Coverage Tracking** with [Codecov](https://codecov.io/)
- ✅ **Performance Benchmarking** with [CodSpeed](https://codspeed.io/)
- ✅ **AI Code Review** with [CodeRabbit](https://coderabbit.ai/)

### DevOps & Infrastructure

- ✅ **Containerization** with [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- ✅ **CI/CD Pipeline** using [GitHub Actions](https://github.com/features/actions)
- ✅ **Automated Versioning** and changelog generation
- ✅ **Multi-environment Deployment** (Preview, Staging, Production)
- ✅ **Full Observability** with [OpenTelemetry](https://opentelemetry.io/) and [SigNoz](https://signoz.io/) integration

---

## 🛠 Tech Stack

> **Note:** Development tools are primarily Rust-based for performance (uv, Ruff, Pyrefly, Prek).

### Development Environment

| Tool | Purpose |
| --- | --- |
| [uv](https://docs.astral.sh/uv/) | Fast Python package manager |
| [Prek](https://prek.j178.dev/) | Pre-validation hooks |
| [Ruff](https://docs.astral.sh/ruff) | Linting & formatting |
| [Pyrefly](https://pyrefly.org/) | Static type verification |
| [Commitizen](https://commitizen-tools.github.io/commitizen/) | Conventional commit enforcement |
| [pytest](https://pytest.org/) | Testing framework |
| [Codecov](https://codecov.io/) | Code coverage tracking & reporting |
| [CodSpeed](https://codspeed.io/) | Performance benchmarking & regression detection |
| [CodeRabbit](https://coderabbit.ai/) | AI-powered code review |

### Backend & Server

| Component | Technology |
| --- | --- |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Server | [FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/) with [Uvicorn](https://www.uvicorn.org/) |
| Database | [PostgreSQL](https://www.postgresql.org/) 17.6 |
| ORM | [SQLModel](https://sqlmodel.tiangolo.com/) |
| Migrations | [Alembic](https://alembic.sqlalchemy.org/) |
| File Storage | [MinIO](https://min.io/) (S3-compatible) |
| Security | [OAuth2](https://oauth.net/2/) ([JWT](https://jwt.io/)) & CORS |

### Observability & Infrastructure

| Tool | Purpose |
| --- | --- |
| [OpenTelemetry](https://opentelemetry.io/) | Instrumentation (traces, metrics, logs) |
| [SigNoz](https://signoz.io/) | Monitoring and tracing platform |
| [Docker](https://www.docker.com/) | Containerization |
| [Docker Compose](https://docs.docker.com/compose/) | Local orchestration |
| [GitHub Actions](https://github.com/features/actions) | CI/CD automation |
| [Coolify](https://coolify.io/) | Deployment platform |

---

## 📂 Project Structure

```text
.
├── app/
│   ├── core/           # Configuration, security, dependencies, telemetry
│   ├── database/       # Database connection and session management
│   ├── internal/       # Admin/internal-only routes
│   ├── models/         # SQLModel tables and Pydantic schemas
│   ├── routers/        # Public API endpoints
│   ├── services/       # Business logic layer
│   ├── utils/          # Utilities (logger, helpers)
│   ├── initial_data.py # Database seeding script
│   └── main.py         # Application entrypoint
├── tests/              # Unit and integration tests
├── alembic/            # Database migration files
│   └── versions/       # Migration history
├── scripts/            # Utility scripts (prestart.sh)
├── .github/
│   └── workflows/      # GitHub Actions CI/CD
├── docker-compose.yml  # Local development stack
├── docker-compose.frontend-dev.yml  # Frontend team setup
├── docker-compose.production.yml  # Production compose (deployment)
├── docker-compose.staging.yml  # Staging compose (deployment)
├── Dockerfile          # Production container image
├── pyproject.toml      # Project configuration
└── uv.lock             # Dependency lock file
```

---

## 🚀 Getting Started

### Prerequisites

- **[Docker](https://www.docker.com/)** & **[Docker Compose](https://docs.docker.com/compose/)** (for containerized development)
- **[Python 3.12+](https://www.python.org/)** (for local development)
- **[uv](https://docs.astral.sh/uv/)** package manager:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Local Development

> [!IMPORTANT]
> This method requires PostgreSQL and MinIO to be running separately. For an all-in-one solution, use the [Docker Setup](#docker-setup) instead.

1. **Clone the repository**

   ```bash
   git clone https://github.com/lyric-s/together-app-backend.git
   cd together-app-backend
   ```

2. **Create and activate virtual environment**

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   uv sync
   ```

4. **Environment setup**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**

   ```bash
   uv run alembic upgrade head
   ```

   For detailed migration documentation, see the [Alembic README](alembic/README.md).

6. **Start the development server**

   ```bash
   uv run fastapi dev app/main.py
   ```

   The API will be available at `http://127.0.0.1:8000`

> [!WARNING]
> Never commit the `.env` file. It contains sensitive credentials. Make sure it in your `.gitignore` if it's not already there. It's normally the case with the one present in the repo but we never know.

### Docker Setup

The easiest way to run the complete stack (API + PostgreSQL + MinIO):

```bash
docker compose up -d --build
```

**Services:**

| Service | URL | Description |
| :--- | :--- | :--- |
| **API** | `http://localhost:8000` | FastAPI Backend |
| **Swagger UI** | `http://localhost:8000/docs` | Interactive API Documentation |
| **ReDoc** | `http://localhost:8000/redoc` | Alternative API Documentation |
| **PostgreSQL** | `localhost:5432` | Database Server (`api_user` / `dev_pass` / `together`) |
| **MinIO API** | `localhost:9000` | S3-compatible Object Storage |
| **MinIO Console** | `http://localhost:9001` | Storage Admin UI (`minioadmin` / `minioadmin`) |

> **Note:** MinIO is pinned to `RELEASE.2025-04-22T22-12-26Z`, the last version with the full admin console UI before MinIO switched to a stripped-down "Community Edition".

**Stop services:**

```bash
docker compose down
```

**Clean restart (remove volumes):**

```bash
docker compose down -v
docker compose up -d --build
```

---

## 🎨 Frontend Development Setup

Frontend developers can run the complete backend stack locally using pre-built Docker images, **without cloning this repository**.

> [!NOTE]
> This setup is designed for frontend teams working on a separate repository. The Docker image is automatically built and published on every push to the `dev` branch.

### Prerequisites for frontend

If you don't have Docker installed yet:

- **Install Docker Desktop**: [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
  - Includes both Docker and Docker Compose
  - Available for Windows, macOS, and Linux
- **Verify installation**: `docker --version` and `docker compose version`

### Quick Start for Frontend Team

#### 1. Login to GitHub Container Registry (one-time setup)

```bash
docker login ghcr.io -u YOUR_GITHUB_USERNAME
```

Use a [Personal Access Token](https://github.com/settings/tokens) with `read:packages` scope as the password.

#### 2. Start the Backend Stack

Download the compose file and start the stack:

**Linux/macOS:**

```bash
curl -o docker-compose.backend.yml https://raw.githubusercontent.com/lyric-s/together-app-backend/dev/docker-compose.frontend-dev.yml
docker compose -f docker-compose.backend.yml up
```

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/lyric-s/together-app-backend/dev/docker-compose.frontend-dev.yml" -OutFile "docker-compose.backend.yml"
docker compose -f docker-compose.backend.yml up
```

> **Tip:** You can combine these into a single command:
>
> ```bash
> curl -o docker-compose.backend.yml https://raw.githubusercontent.com/lyric-s/together-app-backend/dev/docker-compose.frontend-dev.yml && docker compose -f docker-compose.backend.yml up
> ```

### What Gets Started

The stack automatically sets up:

| Service | URL | Credentials |
| :--- | :--- | :--- |
| **API** | `http://localhost:8000` | See [default credentials](#default-credentials) |
| **API Docs (Swagger)** | `http://localhost:8000/docs` | - |
| **MinIO Console** | `http://localhost:9001` | `minioadmin` / `minioadmin123` |

The backend automatically:

- ✅ Pulls the latest dev image
- ✅ Starts PostgreSQL database with schema
- ✅ Starts MinIO object storage (S3-compatible)
- ✅ Runs database migrations
- ✅ Seeds initial data (including superuser)

### Default Credentials

The backend is pre-configured with a test superuser account:

- **Email**: `admin@example.com`
- **Password**: `password`
- **Username**: `admin`

Use these credentials to test authentication endpoints or admin features.

> [!WARNING]
> These are development credentials only. Never use these in production!

### Customizing Environment Variables

If you need to modify any settings (CORS origins, credentials, etc.):

1. **Download the compose file locally** (see Option B above)
2. **Edit the `environment` section** under the `fastapi` service
3. **Available variables**:
   - `BACKEND_CORS_ORIGINS`: Frontend URLs (comma-separated)
   - `FIRST_SUPERUSER_EMAIL`: Admin email
   - `FIRST_SUPERUSER_PASSWORD`: Admin password
   - `SECRET_KEY`: JWT signing key (change for security)
   - And more (see [docker-compose.frontend-dev.yml](docker-compose.frontend-dev.yml))

**Example**: To add your custom frontend port:

```yaml
environment:
  - BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:4200  # Added 4200
```

### Common Commands

```bash
# Stop all services
docker compose -f docker-compose.backend.yml down

# Stop and remove all data (fresh start)
docker compose -f docker-compose.backend.yml down -v

# Update to latest backend version
docker compose -f docker-compose.backend.yml pull
docker compose -f docker-compose.backend.yml up

# View logs
docker compose -f docker-compose.backend.yml logs -f fastapi
```

**Get Updates**:

Re-download the compose file to get updates, or pull the latest image:

```bash
docker compose -f docker-compose.backend.yml up --pull always
```

---

## 📖 API Documentation

The API provides interactive documentation generated automatically from the codebase.

### Swagger UI (`/docs`)

Navigate to `http://localhost:8000/docs`

- Interactive API testing interface
- Try endpoints directly from the browser
- Use the **Authorize** button to authenticate with JWT

### ReDoc (`/redoc`)

Navigate to `http://localhost:8000/redoc`

- Clean, document-style API reference
- Better for reading and understanding the API structure

### OpenAPI Specification

Raw OpenAPI JSON: `http://localhost:8000/openapi.json`

### Additional Documentation

- **[Database Migrations](alembic/README.md)** - Comprehensive guide to using Alembic for schema migrations
- **[Performance Benchmarks](tests/benchmarks/README.md)** - How to write and run performance benchmarks

---

## ✅ Quality Assurance

Code quality is enforced through automated tooling and CI checks.

### Static Analysis

**Linting:**

```bash
uv run ruff check
```

**Auto-fix linting issues:**

```bash
uv run ruff check --fix
```

**Format check:**

```bash
uv run ruff format --check
```

**Auto-format code:**

```bash
uv run ruff format
```

**Type checking:**

```bash
uv run pyrefly check --summarize-errors
```

### Pre-commit Hooks

Validate code before committing:

```bash
uv run prek run --all-files
```

### Testing

Run the test suite:

```bash
uv run pytest
```

**With coverage:**

```bash
uv run pytest --cov=app --cov-report=html
```

**View coverage report:**

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Code Coverage

We use **[Codecov](https://codecov.io/)** to track code coverage across all pull requests:

- **Current Coverage**: Tracked automatically on every commit
- **Coverage Reports**: Posted automatically on every PR
- **Interactive Dashboard**: [View on Codecov](https://codecov.io/gh/lyric-s/together-app-backend)
- **CI Integration**: Coverage runs on every push and PR

**Coverage Goals:**

- **Project Target**: Gradual improvement over time
- **New Code Standard**: New code should be well-tested
- **Threshold**: Reasonable drops allowed without failing CI

The CI automatically uploads coverage reports to Codecov, and the service comments on PRs with:

- Overall coverage change
- Coverage for newly added code
- File-by-file coverage breakdown
- Visual coverage graphs

### Performance Benchmarks

We use **[CodSpeed](https://codspeed.io/)** to track performance regressions:

- **Continuous Benchmarking**: Automated on every PR
- **Performance Tracking**: Detects speed regressions before merge
- **Interactive Dashboard**: [View on CodSpeed](https://codspeed.io/lyric-s/together-app-backend)
- **Lightweight Integration**: Uses `pytest-codspeed` with existing tests

**Running Benchmarks Locally:**

```bash
uv run pytest tests/benchmarks/ --codspeed
```

Benchmarks are located in `tests/benchmarks/` and cover critical operations like user creation, authentication, and database queries. For detailed information about writing and running benchmarks, see the [Benchmarks Documentation](tests/benchmarks/README.md).

### AI-Powered Code Review

We use **[CodeRabbit](https://coderabbit.ai/)** for automated PR reviews:

- Intelligent code suggestions and improvements
- Security vulnerability detection
- Best practices enforcement
- Automated review comments on pull requests

> [!TIP]
> CodeRabbit, Codecov, and CodSpeed work together to provide comprehensive code quality feedback on every PR, catching potential issues before they reach production.

---

## 📊 Observability

The application is fully instrumented with **OpenTelemetry** for production-grade observability.

> [!NOTE]
> The local development environment does not include SigNoz by default to keep it lightweight. The application exports telemetry data when configured with a SigNoz endpoint.

### Observability Configuration

Set these environment variables in `.env`:

```bash
# Telemetry configuration
OTEL_SERVICE_NAME=together-fastapi-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-signoz-endpoint:4317
OTEL_EXPORTER_OTLP_INSECURE=false  # Set to true for insecure (non-TLS) connections

# Environment name (used across all telemetry: traces, metrics, and logs)
ENVIRONMENT=production  # Options: production, staging, development
```

> [!NOTE]
> The application hardcodes gRPC protocol for OTLP exporters. Variables like `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_TRACES_EXPORTER`, `OTEL_METRICS_EXPORTER`, and `OTEL_LOGS_EXPORTER` are not used.

### What's Monitored

Once connected to SigNoz, you can observe:

- **Request Latency** (P99, P95, P50)
- **Database Query Performance**
- **Error Rates and Stack Traces**
- **Application Logs** (aggregated and filterable)
- **Custom Business Metrics**

---

## 🚀 Deployment

The project uses a **hybrid CI/CD strategy** with GitHub Actions and Coolify.

### CI/CD Pipeline

#### 1. Pull Request Validation

**Workflow:** `.github/workflows/development.yml`

On every PR, the pipeline:

- Runs linting (`ruff check`)
- Runs type checking (`pyrefly`)
- Runs tests (`pytest`)
- Validates conventional commit messages (`commitizen`)

#### 2. Staging Deployment (`dev` branch)

**Automatic deployment on merge to `dev`:**

- Coolify builds from source
- Deploys to staging environment
- Available for QA and testing

#### 3. Production Deployment (Version Tags)

**Workflow:** `.github/workflows/deploy-production.yml`

When a version tag is pushed (e.g., `v1.0.0`):

1. GitHub Actions builds the Docker image with OCI metadata
2. Pushes to GitHub Container Registry (`ghcr.io`) with semantic versioning tags
3. Triggers Coolify deployment webhook
4. Waits and verifies deployment health
5. Sends Discord notifications to the team
6. Creates deployment summary with production links

#### 4. Development Image Publishing

**Workflow:** `.github/workflows/build-dev-image.yml`

On every push to `dev`:

- Builds Docker image
- Publishes to `ghcr.io/lyric-s/together-app-backend:dev`
- Used by frontend teams for local development

### Version Management

**Workflow:** `.github/workflows/release.yml`

On merge to `main`:

- Automatically bumps version based on conventional commits
- Generates changelog
- Creates a git tag

---

## 🤝 Contributing

We follow conventional commits for consistent version management and changelog generation.

### Commit Message Format

```text
<type>: <description>

Examples:
feat: add volunteer mission engagement service
fix: correct authentication token validation
docs: update API documentation
```

> **Note:** Earlier commits in this repository include Jira ticket IDs (e.g., `TA-108`) from the original academic project management. New contributions should use standard conventional commits without ticket IDs.

### Commit Types

| Prefix | Description | Version Impact |
| --- | --- | --- |
| `feat:` | New feature | Minor bump |
| `fix:` | Bug fix | Patch bump |
| `docs:` | Documentation only | No bump |
| `style:` | Code formatting (no logic change) | No bump |
| `refactor:` | Code restructuring (no behavior change) | No bump |
| `perf:` | Performance improvement | Patch bump |
| `test:` | Adding or updating tests | No bump |
| `build:` | Build system changes | No bump |
| `ci:` | CI/CD configuration | No bump |
| `chore:` | Maintenance tasks | No bump |
| `revert:` | Revert previous commit | Depends |

### Breaking Changes

Indicate breaking changes with `!` or a footer:

```bash
feat!: change authentication method to OAuth2

BREAKING CHANGE: API authentication now requires OAuth2 tokens
```

This triggers a **major version bump**.

[Source: Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#specification)

---

## 🎯 Using as a Template

This project is designed to be reusable as a starting point for your own FastAPI applications. We acknowledge that our choices may not have been the best as we were still learning when making this project. Improve it to your heart's content.

### What's Included

- ✅ **Production-ready architecture** with separation of concerns
- ✅ **Complete authentication system** with [JWT](https://jwt.io/) tokens
- ✅ **Database setup** with migrations and seeding
- ✅ **File upload/storage** with [MinIO](https://min.io/) integration
- ✅ **Full observability** with [OpenTelemetry](https://opentelemetry.io/)
- ✅ **CI/CD pipelines** ready to customize
- ✅ **[Docker](https://www.docker.com/) configuration** for development and production
- ✅ **Code quality tools** pre-configured

### Customization Steps

1. **Fork or clone** this repository
2. **Update branding:**
   - Change `OTEL_SERVICE_NAME` in `.env.example`
   - Update repository references in workflows
   - Replace `together` database name in configs
3. **Remove Together-specific code:**
   - Delete domain-specific models in `app/models/`
   - Remove business logic in `app/services/`
   - Clean up routers in `app/routers/`
4. **Add your domain logic:**
   - Create your models
   - Implement your business logic
   - Define your API endpoints
5. **Update documentation:**
   - Replace this README with your project details
   - Update LICENSE if needed

### Potential Improvements

- **Rate limiting** with [slowapi](https://github.com/laurentS/slowapi) or custom middleware
- **Caching** with [Redis](https://redis.io/) for frequently accessed data
- **Background tasks** with [Celery](https://docs.celeryq.dev/) or [ARQ](https://arq-docs.helpmanual.io/)
- **WebSocket support** for real-time features
- **GraphQL API** with [Strawberry](https://strawberry.rocks/) alongside REST endpoints
- **Multi-tenancy** architecture
- **API versioning** strategy (URL or header-based)
- **Advanced monitoring** with custom metrics and alerts
- **Security scanning** with [Trivy](https://trivy.dev/) or [Snyk](https://snyk.io/) in CI/CD pipeline
- **Load testing** with [Locust](https://locust.io/) or [k6](https://k6.io/)
- **Feature flags** for gradual rollouts

---

## 🌐 Project Links

### Related Repositories

- **Frontend Application**: [together-app](https://github.com/lyric-s/together-app) - React-based web interface for the Together platform

### Live Demos

- **Production API**: [https://together-api.out-online.net](https://together-api.out-online.net)
- **API Documentation**: [https://together-api.out-online.net/docs](https://together-api.out-online.net/docs) - Interactive Swagger UI
- **Staging Environment**: _Internal deployment for testing_

---

## 🏗️ Infrastructure & Architecture

This project demonstrates a **fully self-hosted infrastructure** built primarily on open-source technologies, showcasing enterprise-grade deployment practices on a budget.

> [!NOTE]
> Our infrastructure is entirely self-hosted, providing hands-on experience with real-world DevOps practices and infrastructure management.

### Infrastructure Stack

#### Virtualization & Compute

- **[Proxmox VE](https://www.proxmox.com/)** - Hypervisor platform hosting all virtual machines and containers
- **[Patchmon](https://github.com/colinmurphy1/patchmon)** - Automated monitoring and management of Proxmox LXC containers

#### Deployment & Orchestration

- **[Coolify](https://coolify.io/)** - Self-hosted PaaS for deploying applications
  - Handles preview deployments (PRs)
  - Manages staging environment (`dev` branch)
  - Deploys production from Docker images
- **[Portainer](https://www.portainer.io/)** - Docker container management interface
  - Runs on Raspberry Pi 5
  - Centralized container monitoring

#### Data Storage & Management

- **[PostgreSQL 17.6](https://www.postgresql.org/)** - Primary database
- **[pgAdmin](https://www.pgadmin.org/)** - Database administration interface
- **[MinIO](https://min.io/)** - S3-compatible object storage for file uploads
- **[TrueNAS](https://www.truenas.com/)** - Network-attached storage for backups and data persistence

#### Observability & Monitoring

- **[SigNoz](https://signoz.io/)** - Open-source observability platform
  - Distributed tracing
  - Metrics collection and visualization
  - Centralized log aggregation
  - Application performance monitoring (APM)

#### Networking & Edge

- **[Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/)** - Edge network gateway running:
  - **[Nginx Proxy Manager](https://nginxproxymanager.com/)** - Reverse proxy with SSL/TLS management
  - **[Portainer](https://www.portainer.io/)** - Container orchestration
- **[Cloudflare](https://www.cloudflare.com/)** - DNS and edge routing
  - Route traffic from the internet to internal services
  - DDoS protection and caching

> [!NOTE]
> We initially planned to migrate from Cloudflare to [Pangolin](https://github.com/wangzhao-dev/pangolin) (open-source alternative) but time constraints prevented this. Future improvement opportunity!

### Architecture Highlights

**Why Self-Hosted?**

- **Learning Experience**: Hands-on exposure to infrastructure management
- **Cost Efficiency**: Eliminate cloud provider costs for academic projects
- **Full Control**: Complete visibility into the entire stack
- **Open-Source-First**: Commitment to FOSS tools and transparency
- **Homelabbing is cool**: 😎

**Network Flow:**

```text
Internet Traffic
    ↓
Cloudflare DNS & Edge
    ↓
Raspberry Pi 5 (Nginx Proxy Manager)
    ↓
Proxmox Cluster
    ↓
┌─────────────┬──────────────┬──────────────┬──────────────┐
│  Coolify    │  PostgreSQL  │    MinIO     │   SigNoz     │
│  (Deploy)   │  (Database)  │  (Storage)   │  (Observ.)   │
└─────────────┴──────────────┴──────────────┴──────────────┘
         ↓              ↓              ↓              ↓
    FastAPI App    Persistent    File Storage    Telemetry
                      Data          Layer          Data
```

**Backup Strategy:**

- TrueNAS provides automated snapshots and backups for all critical data

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Copyright © 2025-2026 IUT Paris - Rives de Seine

---

## 🎓 Academic Context

This project was developed as part of an academic curriculum at **IUT Paris - Rives de Seine**, a branch of the **University of Paris**.

**Project Goal:** Build a realistic, production-ready backend API demonstrating modern software engineering practices, DevOps workflows, and full-stack observability, with an ethical or environmental dimension.

**Fictional Platform:** "Together" is a conceptual volunteer coordination platform created for educational purposes.

**Unimplemented Features:** Some planned features were not completed due to time constraints. You may find partial implementations (models, schemas) in the codebase for:

- Personalized mission tracking
- Symbolic rewards system (badges, achievements)

---

Built with ❤️ at IUT Paris - Rives de Seine

[Report an Issue](https://github.com/Lyric-s/together-app-backend/issues) · [Request a Feature](https://github.com/Lyric-s/together-app-backend/issues)
