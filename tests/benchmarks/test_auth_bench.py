"""Performance benchmarks for authentication operations."""

import pytest
from pytest_codspeed import BenchmarkFixture

from app.core.password import get_password_hash, verify_password


@pytest.fixture(name="test_password")
def test_password_fixture():
    """Provide test password for benchmarks."""
    return "SecureTestPassword123!"


@pytest.fixture(name="hashed_password")
def hashed_password_fixture(test_password: str):
    """Provide pre-hashed password for verification benchmarks."""
    return get_password_hash(test_password)


def test_password_hashing_performance(benchmark: BenchmarkFixture, test_password: str):
    """Benchmark password hashing with Argon2."""

    @benchmark
    def hash_password():
        return get_password_hash(test_password)


def test_password_verification_performance(
    benchmark: BenchmarkFixture, test_password: str, hashed_password: str
):
    """Benchmark password verification with Argon2."""

    @benchmark
    def verify():
        return verify_password(test_password, hashed_password)


def test_password_verification_failure_performance(
    benchmark: BenchmarkFixture, hashed_password: str
):
    """Benchmark password verification with incorrect password."""
    wrong_password = "WrongPassword456!"

    @benchmark
    def verify_wrong():
        return verify_password(wrong_password, hashed_password)
