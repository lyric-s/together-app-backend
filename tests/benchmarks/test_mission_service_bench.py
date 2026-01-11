"""Performance benchmarks for mission service operations."""

from datetime import date, timedelta
import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.mission import MissionCreate
from app.services import mission as mission_service
from app.services import association as association_service
from app.models.location import Location
from app.models.category import Category


@pytest.fixture(name="mission_setup_data")
def mission_setup_fixture(
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
    location_create_data_factory,
    category_create_data_factory,
):
    """Setup dependencies for mission creation."""
    association = association_service.create_association(
        session=session,
        user_in=user_create_data_factory(),
        association_in=association_create_data_factory(),
    )
    location = Location.model_validate(location_create_data_factory())
    session.add(location)
    category = Category.model_validate(category_create_data_factory())
    session.add(category)
    session.flush()

    return {
        "id_asso": association.id_asso,
        "id_location": location.id_location,
        "category_ids": [category.id_categ],
    }


def test_mission_creation_performance(
    benchmark: BenchmarkFixture, session: Session, mission_setup_data, tracker
):
    """Benchmark mission creation operation."""

    @benchmark
    def create_mission():
        mission_in = MissionCreate(
            name="Bench Mission",
            description="Benchmark mission description",
            date_start=date.today(),
            date_end=date.today() + timedelta(days=1),
            skills="Benchmark skills",
            capacity_min=1,
            capacity_max=10,
            id_asso=mission_setup_data["id_asso"],
            id_location=mission_setup_data["id_location"],
            category_ids=mission_setup_data["category_ids"],
        )
        mission = mission_service.create_mission(session=session, mission_in=mission_in)
        tracker.append(mission)
        return mission.id_mission


def test_mission_retrieval_performance(
    benchmark: BenchmarkFixture, session: Session, mission_setup_data
):
    """Benchmark mission retrieval by ID operation."""
    mission_in = MissionCreate(
        name="Bench Mission",
        description="Benchmark mission description",
        date_start=date.today(),
        date_end=date.today() + timedelta(days=1),
        skills="Benchmark skills",
        capacity_min=1,
        capacity_max=10,
        id_asso=mission_setup_data["id_asso"],
        id_location=mission_setup_data["id_location"],
        category_ids=mission_setup_data["category_ids"],
    )
    mission = mission_service.create_mission(session=session, mission_in=mission_in)
    session.flush()
    mission_id = mission.id_mission

    @benchmark
    def get_mission():
        session.expire_all()
        assert mission_id is not None
        return mission_service.get_mission(session=session, mission_id=mission_id)


def test_mission_search_performance(
    benchmark: BenchmarkFixture, session: Session, mission_setup_data
):
    """Benchmark mission search operation."""
    # Setup: Create some missions
    for i in range(10):
        mission_in = MissionCreate(
            name=f"Bench Mission {i}",
            description="Benchmark mission description",
            date_start=date.today(),
            date_end=date.today() + timedelta(days=1),
            skills="Benchmark skills",
            capacity_min=1,
            capacity_max=10,
            id_asso=mission_setup_data["id_asso"],
            id_location=mission_setup_data["id_location"],
            category_ids=mission_setup_data["category_ids"],
        )
        mission_service.create_mission(session=session, mission_in=mission_in)
    session.flush()

    @benchmark
    def search_missions():
        session.expire_all()
        return mission_service.search_missions(session=session, search="Bench")
