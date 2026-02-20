"""Schemathesis API security testing.

Simple property-based testing for API security using Schemathesis.

Usage:
    # Using CLI (simplest - no pytest needed):
    uv run schemathesis run http://127.0.0.1:8000/openapi.json

    # Or with pytest:
    uv run pytest tests/security/test_schemathesis_api.py -v -m security

Prerequisites:
    - API server must be running: uv run fastapi dev app/main.py
"""

import pytest
import schemathesis

# Load schema from running API server
schema = schemathesis.openapi.from_url("http://127.0.0.1:8000/openapi.json")


@pytest.mark.security
@schema.parametrize()
def test_api(case):
    """Test all API endpoints for common vulnerabilities."""
    case.call_and_validate()
