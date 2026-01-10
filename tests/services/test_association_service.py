"""Tests for association service CRUD operations."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.association import (
    Association,
    AssociationCreate,
    AssociationUpdate,
)
from app.models.mission import Mission
from app.models.location import Location
from app.models.category import Category
from app.models.enums import UserType
from app.services import association as association_service
from app.services import user as user_service
from app.exceptions import NotFoundError, ValidationError, AlreadyExistsError

# Test data constants
TEST_ASSO_USERNAME = "asso_user"
TEST_ASSO_EMAIL = "asso@example.com"
TEST_ASSO_PASSWORD = "Password123"
TEST_ASSO_NAME = "Hearts for Community"
TEST_ASSO_ADDRESS = "42 Boulevard Saint-Germain"
TEST_ASSO_COUNTRY = "France"
TEST_ASSO_PHONE = "+33145678900"
TEST_ASSO_ZIP = "75005"
TEST_ASSO_RNA = "W751234567"
TEST_ASSO_COMPANY = "Association Hearts for Community"

NONEXISTENT_ID = 99999


@pytest.fixture(name="sample_user_create_asso")
def sample_user_create_asso_fixture():
    return UserCreate(
        username=TEST_ASSO_USERNAME,
        email=TEST_ASSO_EMAIL,
        password=TEST_ASSO_PASSWORD,
        user_type=UserType.ASSOCIATION,
    )


@pytest.fixture(name="sample_association_create")
def sample_association_create_fixture():
    return AssociationCreate(
        name=TEST_ASSO_NAME,
        address=TEST_ASSO_ADDRESS,
        country=TEST_ASSO_COUNTRY,
        phone_number=TEST_ASSO_PHONE,
        zip_code=TEST_ASSO_ZIP,
        rna_code=TEST_ASSO_RNA,
        company_name=TEST_ASSO_COMPANY,
        description="Test Association Description",
    )


@pytest.fixture(name="created_association")
def created_association_fixture(
    session: Session,
    sample_user_create_asso: UserCreate,
    sample_association_create: AssociationCreate,
) -> Association:
    association = association_service.create_association(
        session, sample_user_create_asso, sample_association_create
    )
    return association


class TestCreateAssociation:
    def test_create_association_success(self, created_association: Association):
        assert created_association.id_asso is not None
        assert created_association.name == TEST_ASSO_NAME
        assert created_association.rna_code == TEST_ASSO_RNA
        assert created_association.user.username == TEST_ASSO_USERNAME
        assert created_association.user.user_type == UserType.ASSOCIATION

    def test_create_association_invalid_rna(
        self,
        session: Session,
        sample_user_create_asso: UserCreate,
        sample_association_create: AssociationCreate,
    ):
        invalid_rna = sample_association_create.model_copy()
        invalid_rna.rna_code = "INVALID123"  # No 'W' prefix, wrong length

        with pytest.raises(ValidationError) as exc_info:
            association_service.create_association(
                session, sample_user_create_asso, invalid_rna
            )
        assert "Invalid RNA code format" in str(exc_info.value)

    def test_create_association_duplicate_user(
        self,
        session: Session,
        sample_user_create_asso: UserCreate,
        sample_association_create: AssociationCreate,
    ):
        association_service.create_association(
            session, sample_user_create_asso, sample_association_create
        )
        with pytest.raises(AlreadyExistsError):
            association_service.create_association(
                session, sample_user_create_asso, sample_association_create
            )


class TestGetAssociation:
    def test_get_association_by_id(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        fetched = association_service.get_association(
            session, created_association.id_asso
        )
        assert fetched is not None
        assert fetched.id_asso == created_association.id_asso
        assert fetched.user.email == TEST_ASSO_EMAIL

    def test_get_association_by_user_id(
        self, session: Session, created_association: Association
    ):
        fetched = association_service.get_association_by_user_id(
            session, created_association.id_user
        )
        assert fetched is not None
        assert fetched.id_asso == created_association.id_asso

    def test_get_association_not_found(self, session: Session):
        assert association_service.get_association(session, NONEXISTENT_ID) is None


class TestUpdateAssociation:
    def test_update_association_profile(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        update_data = AssociationUpdate(name="New Name", description="Updated desc")
        updated = association_service.update_association(
            session, created_association.id_asso, update_data
        )
        assert updated.name == "New Name"
        assert updated.description == "Updated desc"
        assert updated.rna_code == TEST_ASSO_RNA  # Unchanged

    def test_update_association_rna_valid(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        new_rna = "W987654321"
        update_data = AssociationUpdate(rna_code=new_rna)
        updated = association_service.update_association(
            session, created_association.id_asso, update_data
        )
        assert updated.rna_code == new_rna

    def test_update_association_rna_invalid(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        update_data = AssociationUpdate(rna_code="BADFORMAT")
        with pytest.raises(ValidationError):
            association_service.update_association(
                session, created_association.id_asso, update_data
            )

    def test_update_association_user_info(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        new_email = "new_asso@example.com"
        update_data = AssociationUpdate(email=new_email)
        updated = association_service.update_association(
            session, created_association.id_asso, update_data
        )
        assert updated.user.email == new_email

    def test_update_association_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            association_service.update_association(
                session, NONEXISTENT_ID, AssociationUpdate(name="New Name")
            )


class TestDeleteAssociation:
    def test_delete_association_success(
        self, session: Session, created_association: Association
    ):
        assert created_association.id_asso is not None
        association_service.delete_association(session, created_association.id_asso)
        assert (
            association_service.get_association(session, created_association.id_asso)
            is None
        )
        assert user_service.get_user(session, created_association.id_user) is None

    def test_delete_association_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            association_service.delete_association(session, NONEXISTENT_ID)


class TestAssociationMissionCounts:
    def test_mission_counts(self, session: Session, created_association: Association):
        """
        Verifies that an association's active and finished mission counts are computed correctly.
        """
        assert created_association.id_asso is not None

        # Helper to create missions
        location = Location(address="123 St", country="France", zip_code="75001")
        session.add(location)
        category = Category(label="Test")
        session.add(category)
        session.commit()

        today = date.today()

        # Mission 1: Active (ends in future)
        m1 = Mission(
            name="Active Mission",
            id_location=location.id_location,
            id_categ=category.id_categ,
            id_asso=created_association.id_asso,
            date_start=today,
            date_end=today + timedelta(days=10),
            skills="None",
            description="Desc",
            capacity_min=1,
            capacity_max=5,
        )

        # Mission 2: Finished (ended yesterday)
        m2 = Mission(
            name="Finished Mission",
            id_location=location.id_location,
            id_categ=category.id_categ,
            id_asso=created_association.id_asso,
            date_start=today - timedelta(days=10),
            date_end=today - timedelta(days=1),
            skills="None",
            description="Desc",
            capacity_min=1,
            capacity_max=5,
        )

        session.add(m1)
        session.add(m2)
        session.commit()

        # Check counts via to_association_public helper
        public_asso = association_service.to_association_public(
            session, created_association
        )
        assert public_asso.active_missions_count == 1
        assert public_asso.finished_missions_count == 1

    def test_get_associations_batch_counts(
        self,
        session: Session,
        sample_user_create_asso: UserCreate,
        sample_association_create: AssociationCreate,
    ):
        # Create 2 associations
        assos = []
        for i in range(2):
            u_create = sample_user_create_asso.model_copy()
            u_create.username = f"asso_batch_{i}"
            u_create.email = f"asso_batch_{i}@example.com"

            a_create = sample_association_create.model_copy()
            a_create.name = f"Asso {i}"
            a_create.rna_code = f"W{i}23456789"  # Valid RNA

            asso = association_service.create_association(session, u_create, a_create)
            assos.append(asso)

        # Setup missions
        location = Location(address="123 St", country="France", zip_code="75001")
        session.add(location)
        category = Category(label="Test")
        session.add(category)
        session.commit()

        today = date.today()

        # Asso 0: 2 active missions
        for _ in range(2):
            session.add(
                Mission(
                    name="Active Mission",
                    id_location=location.id_location,
                    id_categ=category.id_categ,
                    id_asso=assos[0].id_asso,
                    date_start=today,
                    date_end=today + timedelta(days=10),
                    skills="None",
                    description="Desc",
                    capacity_min=1,
                    capacity_max=5,
                )
            )

        # Asso 1: 1 finished mission
        session.add(
            Mission(
                name="Finished Mission",
                id_location=location.id_location,
                id_categ=category.id_categ,
                id_asso=assos[1].id_asso,
                date_start=today - timedelta(days=10),
                date_end=today - timedelta(days=1),
                skills="None",
                description="Desc",
                capacity_min=1,
                capacity_max=5,
            )
        )

        session.commit()

        # Fetch batch
        results = association_service.get_associations(session)

        # Sort and filter
        our_results = [r for r in results if r.name.startswith("Asso ")]
        our_results.sort(key=lambda x: x.name)

        assert len(our_results) == 2

        # Asso 0
        assert our_results[0].active_missions_count == 2
        assert our_results[0].finished_missions_count == 0

        # Asso 1
        assert our_results[1].active_missions_count == 0
        assert our_results[1].finished_missions_count == 1
