"""
Benchmark tests for the synchronous, local AI moderation service.
"""

import asyncio
import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session
from datetime import date

from app.services.ai_moderation_service import AIModerationService
from app.models.enums import ReportTarget, UserType
from app.models.user import UserCreate
from app.models.volunteer import Volunteer
from app.services import user as user_service
from tests.services.test_ai_moderation_service import MockAIModerationClient

@pytest.fixture
def ai_service():
    """Provides a service with a mock client for benchmarks."""
    return AIModerationService(MockAIModerationClient())

@pytest.fixture(name="volunteer_user")
def volunteer_user_fixture(session: Session):
    """Creates a volunteer user for benchmark tests."""
    user_create = UserCreate(
        username="bench_vol_local",
        email="bench_vol_local@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)

    volunteer = Volunteer(
        id_user=user.id_user,
        first_name="Bench",
        last_name="Local",
        phone_number="0123456789",
        birthdate=date(1990, 1, 1),
        bio=""
    )
    session.add(volunteer)
    session.commit()
    session.refresh(user)
    return user

class TestAIModerationServiceBenchmarks:
    """Benchmarks for the AI service logic."""

    def test_moderate_content_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        ai_service: AIModerationService,
        volunteer_user,
    ):
        """Benchmarks the moderate_content logic."""
        
        user_id = volunteer_user.id_user
        text = "Normal text for benchmark"
        
        # Benchmark wrapper for async method
        def run_moderate():
            asyncio.run(ai_service.moderate_content(
                session, 
                ReportTarget.PROFILE, 
                user_id, 
                user_id, # reported_user_id
                text
            ))

        benchmark(run_moderate)

    def test_batch_moderation_logic_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        ai_service: AIModerationService,
        volunteer_user,
    ):
        """Benchmarks the batch moderation logic."""
        
        volunteer_user.volunteer_profile.bio = "Benchmarking batch scan content"
        session.add(volunteer_user)
        session.commit()

        # Benchmark wrapper for async method
        def run_batch():
            asyncio.run(ai_service.run_batch_moderation(session))

        benchmark(run_batch)