"""Performance benchmarks for authentication operations."""

import pytest
from pytest_codspeed import BenchmarkFixture

from app.core.password import get_password_hash, verify_password


@pytest.fixture(name="test_password")
def test_password_fixture():
    """
    Provide a reproducible plaintext password used by benchmark tests.

    Returns:
        str: The constant test password "SecureTestPassword123!".
    """
    return "SecureTestPassword123!"


@pytest.fixture(name="hashed_password")
def hashed_password_fixture(test_password: str):
    """
    Provide a pre-hashed password derived from the given plaintext for verification benchmarks.

    Parameters:
        test_password (str): Plaintext password to be hashed for use in benchmarked verification.

    Returns:
        str: Password hash suitable for verification (as produced by the application's hashing utility).
    """
    return get_password_hash(test_password)


def test_password_hashing_performance(benchmark: BenchmarkFixture, test_password: str):
    """Benchmark password hashing with Argon2."""

    @benchmark
    def hash_password():
        """
        Produce a hashed representation of the benchmark test password.

        Returns:
            str: Argon2 hash of the `test_password` fixture.
        """
        return get_password_hash(test_password)


def test_password_verification_performance(
    benchmark: BenchmarkFixture, test_password: str, hashed_password: str
):
    """
    Benchmark verification of a correct password against its Argon2 hash.

    Uses the provided `benchmark` fixture to measure the performance of verifying `test_password` against `hashed_password`.
    """

    @benchmark
    def verify():
        return verify_password(test_password, hashed_password)


def test_password_verification_failure_performance(
    benchmark: BenchmarkFixture, hashed_password: str
):
    """
    Measure performance of verifying an incorrect password against a valid hash.

    Parameters:
        hashed_password (str): A valid password hash used as the verification target.
    """
    wrong_password = "WrongPassword456!"

    @benchmark
    def verify_wrong():
        """
        Check whether a known-incorrect password matches the provided hashed password.

        Returns:
            bool: `True` if `wrong_password` matches `hashed_password`, `False` otherwise.
        """
        return verify_password(wrong_password, hashed_password)
