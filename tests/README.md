# Test Suite for Together App Backend

This directory contains comprehensive unit tests for the Together App Backend FastAPI application.

## Test Coverage

### Core Modules

- **test_core_config.py** - Tests for application configuration and settings
  - Settings creation and validation
  - Environment variable loading
  - LRU cache behavior
  - CORS origins configuration
  - Edge cases and validation errors

- **test_core_security.py** - Tests for authentication and security
  - Password hashing and verification
  - User and admin authentication
  - JWT token creation and validation
  - Access and refresh token generation
  - Token expiration handling
  - Security edge cases (SQL injection, timing attacks)

- **test_core_dependencies.py** - Tests for FastAPI dependencies
  - Current user extraction from JWT
  - Current admin extraction from JWT
  - Token validation and error handling
  - OAuth2 scheme configuration
  - Invalid token handling

- **test_core_telemetry.py** - Tests for OpenTelemetry integration
  - Telemetry setup and configuration
  - Resource attribute configuration
  - Instrumentation setup
  - Exception handling
  - Endpoint exclusion

### API Routers

- **test_routers_auth.py** - Tests for authentication endpoints
  - Login endpoint (`/auth/token`)
  - Token refresh endpoint (`/auth/refresh`)
  - Success and failure scenarios
  - Validation errors
  - Security considerations
  - Full authentication flow integration

- **test_internal_admin.py** - Tests for admin management
  - Admin login endpoint
  - Admin creation endpoint
  - Authentication and authorization
  - Duplicate username/email handling
  - Password hashing verification

### Utilities

- **test_utils_logger.py** - Tests for logging configuration
  - InterceptHandler for log redirection
  - OpenTelemetry log integration
  - Logger hijacking for standard libraries
  - Exception handling in logging
  - Async safety configuration

### Models

- **test_models.py** - Tests for Pydantic/SQLModel models
  - User models (User, UserCreate, UserPublic, UserUpdate)
  - Admin models (Admin, AdminCreate, AdminPublic, AdminUpdate)
  - Token models (Token, TokenData, TokenRefreshRequest)
  - Enum types (UserType, ProcessingStatus)
  - Model validation and serialization

### Database

- **test_database.py** - Tests for database operations
  - Database engine configuration
  - Session management
  - Table creation
  - Transaction handling (commit, rollback)
  - CRUD operations

### Application

- **test_main.py** - Tests for main FastAPI application
  - App configuration
  - CORS middleware
  - Health endpoint
  - Favicon endpoint
  - Router inclusion
  - Lifespan events
  - OpenAPI schema
  - Error handling

## Test Structure

All tests follow these conventions:

- **Class-based organization** - Tests are organized into classes by functionality
- **Descriptive names** - Test names clearly describe what is being tested
- **Fixtures** - Shared test fixtures in `conftest.py`
- **Mocking** - External dependencies are mocked where appropriate
- **Edge cases** - Comprehensive coverage of edge cases and error conditions

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_core_security.py
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test class
```bash
pytest tests/test_core_security.py::TestPasswordHashing
```

### Run specific test
```bash
pytest tests/test_core_security.py::TestPasswordHashing::test_verify_password_correct_password
```

## Test Fixtures (conftest.py)

### Available Fixtures

- **test_settings** - Mock application settings
- **override_get_settings** - Override get_settings dependency
- **test_engine** - In-memory SQLite engine for testing
- **test_session** - Test database session
- **test_user** - Pre-created test user
- **test_admin** - Pre-created test admin
- **mock_session** - Mock session for unit tests

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test interaction between components
- Use test database
- Verify end-to-end flows

### Security Tests
- SQL injection prevention
- Timing attack resistance
- Authentication and authorization
- Token validation

### Edge Case Tests
- Empty values
- Very long strings
- Unicode characters
- Invalid inputs
- Boundary conditions

## Best Practices

1. **Isolation** - Each test is independent and can run in any order
2. **Cleanup** - Tests clean up after themselves
3. **Clear Assertions** - Each test has clear, specific assertions
4. **Mocking** - External services and I/O are mocked
5. **Coverage** - Happy paths, error cases, and edge cases are covered
6. **Documentation** - Each test has a clear docstring

## Adding New Tests

When adding new tests:

1. Follow existing naming conventions
2. Add appropriate docstrings
3. Use fixtures from conftest.py
4. Mock external dependencies
5. Test both success and failure scenarios
6. Include edge cases
7. Keep tests focused and atomic

## Dependencies

Tests use:
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **unittest.mock** - Mocking framework
- **FastAPI TestClient** - API testing
- **SQLModel** - Database testing

## Coverage Goals

Aim for:
- 90%+ line coverage
- 85%+ branch coverage
- All public APIs tested
- All error paths tested
- Edge cases covered