"""Benchmark tests for AI moderation service operations."""

import pytest
import asyncio
from datetime import date
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services.ai_moderation_service import AIModerationService
from app.models.enums import ReportTarget, UserType
from app.models.user import UserCreate
from app.models.volunteer import Volunteer
from app.services import user as user_service
from tests.services.test_ai_moderation_service import MockAIModerationClient

@pytest.fixture
def ai_service():
    """AI service with mock client for benchmarks."""
    return AIModerationService(MockAIModerationClient())

@pytest.fixture(name="volunteer_user")
def volunteer_user_fixture(session: Session):
    """Create a volunteer user with profile for benchmarks."""
    user_create = UserCreate(
        username="bench_vol",
        email="bench_vol@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)

    volunteer = Volunteer(
        id_user=user.id_user,
        first_name="Bench",
        last_name="Volunteer",
        phone_number="0123456789",
        birthdate=date(1990, 1, 1),
        bio=""
    )
    session.add(volunteer)
    session.commit()
    session.refresh(user)
    return user

class TestAIModerationServiceBenchmarks:
    """Benchmark AI moderation service logic."""

    def test_moderate_content_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        ai_service,
        volunteer_user,
    ):
        """Benchmark the moderate_content logic (with mock AI)."""
        
        # On utilise l'ID réel de l'utilisateur créé pour le test
        user_id = volunteer_user.id_user
        
        def sync_moderate():
            asyncio.run(ai_service.moderate_content(
                session, 
                ReportTarget.PROFILE, 
                user_id, 
                "Normal text for benchmark"
            ))

        benchmark(sync_moderate)

    def test_batch_moderation_logic_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        ai_service,
        volunteer_user,
    ):
        """Benchmark the batch moderation candidate selection and processing logic."""
        
        # Préparation des données
        volunteer_user.volunteer_profile.bio = "Benchmarking batch scan content"
        session.add(volunteer_user)
        session.commit()

        def sync_batch():
            asyncio.run(ai_service.run_batch_moderation(session))

        benchmark(sync_batch)
