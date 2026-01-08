# Performance Benchmarks

This directory contains performance benchmarks for the Together API using [pytest-codspeed](https://github.com/CodSpeedHQ/pytest-codspeed).

## Running Benchmarks

### Run all benchmarks

```bash
uv run pytest tests/benchmarks/ --codspeed
```

### Run specific benchmark file

```bash
uv run pytest tests/benchmarks/test_user_service_bench.py --codspeed
```

### Run benchmarks without CodSpeed instrumentation (faster locally)

```bash
uv run pytest tests/benchmarks/
```

## Writing Benchmarks

Benchmarks use the `BenchmarkFixture` from pytest-codspeed:

```python
from pytest_codspeed import BenchmarkFixture

def test_operation_performance(benchmark: BenchmarkFixture, session: Session):
    """Benchmark description."""

    @benchmark
    def operation():
        # Code to benchmark
        return result
```

### Best Practices

1. **Use descriptive names**: `test_user_creation_performance` not `test_bench1`
2. **Clean up between iterations**: Remove test data to avoid side effects
3. **Benchmark realistic operations**: Focus on actual user-facing operations
4. **Isolate the operation**: Setup data outside the benchmark decorator
5. **Keep it lightweight**: Benchmarks should complete quickly

## What to Benchmark

Focus on:

- **Database operations**: CRUD operations, complex queries
- **Authentication**: Password hashing, token generation
- **Business logic**: Service layer operations
- **API endpoints**: Critical user-facing endpoints (future)
- **Data processing**: Serialization, validation

Avoid:

- Network calls (mock them)
- File I/O (use in-memory alternatives)
- External dependencies

## Current Benchmarks

### User Service (`test_user_service_bench.py`)
- `test_user_creation_performance`: Measures user creation with password hashing
- `test_user_retrieval_by_id_performance`: Measures user retrieval by ID
- `test_user_retrieval_by_email_performance`: Measures user retrieval by email

### Authentication (`test_auth_bench.py`)
- `test_password_hashing_performance`: Measures Argon2 password hashing
- `test_password_verification_performance`: Measures password verification (correct)
- `test_password_verification_failure_performance`: Measures password verification (incorrect)

### Volunteer Service (`test_volunteer_service_bench.py`)
- `test_volunteer_creation_performance`: Measures volunteer profile creation
- `test_volunteer_retrieval_performance`: Measures volunteer retrieval by ID

## CI Integration

Benchmarks automatically run on every PR via GitHub Actions and report to [CodSpeed](https://codspeed.io/lyric-s/together-app-backend).

Performance regressions are detected and commented on PRs before merge.

## Understanding Results

- **Baseline**: First benchmark run establishes a baseline
- **Comparison**: Subsequent runs compare against baseline
- **Regression**: Performance decrease triggers a warning
- **Improvement**: Performance increase is highlighted

CodSpeed tracks performance trends over time and helps identify:
- Slow database queries
- Inefficient algorithms
- Performance regressions from code changes
