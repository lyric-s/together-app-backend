"""
AI-specific test data initialization module.

This module provides functions to seed the database with suspicious content
(spam and toxic language) specifically designed to test the AI moderation system.
It is intended for use in development and staging environments.
"""

from loguru import logger
from sqlmodel import Session, select
from datetime import date

from app.models.user import UserCreate, User
from app.models.volunteer import VolunteerCreate
from app.models.association import AssociationCreate, Association
from app.models.mission import MissionCreate, Mission
from app.models.enums import UserType, ProcessingStatus
from app.services import volunteer as volunteer_service
from app.services import association as association_service
from app.services import mission as mission_service
from app.services import location as location_service
from app.models.location import LocationCreate, Location
from app.models.category import Category


def init_ai_test_data(session: Session) -> None:
    """
    Seeds the database with suspicious content to test AI moderation logic.

    This function creates:
    - A volunteer with a spam-like bio.
    - A volunteer with toxic language in their bio.
    - A mission with a suspicious/fraudulent description.

    The data is only created if it doesn't already exist (idempotent).

    Args:
        session (Session): The database session to use for seeding.
    """
    logger.info("Seeding AI test data...")
    pwd = "password123"

    # 1. Suspicious Volunteer (Spam)
    if not session.exec(
        select(User).where(User.email == "spam_user@example.com")
    ).first():
        volunteer_service.create_volunteer(
            session,
            UserCreate(
                username="spam_bot",
                email="spam_user@example.com",
                password=pwd,
                user_type=UserType.VOLUNTEER,
            ),
            VolunteerCreate(
                first_name="Spam",
                last_name="Bot",
                phone_number="0699999999",
                birthdate=date(1990, 1, 1),
                bio="Gagnez 5000€ par jour sans rien faire ! Cliquez ici pour devenir riche spam spam !.",
                skills="Fraud, Phishing",
            ),
        )

    # 2. Toxic Volunteer
    if not session.exec(
        select(User).where(User.email == "toxic_user@example.com")
    ).first():
        volunteer_service.create_volunteer(
            session,
            UserCreate(
                username="toxic_user",
                email="toxic_user@example.com",
                password=pwd,
                user_type=UserType.VOLUNTEER,
            ),
            VolunteerCreate(
                first_name="Toxic",
                last_name="Person",
                phone_number="0688888888",
                birthdate=date(1992, 2, 2),
                bio="Je déteste tout le monde, foutez le camp d'ici ! Inutile de me contacter.",
                skills="Insults, Rudeness",
            ),
        )

    # 3. Suspicious Mission (Spam)
    # Check/Create Location
    loc = session.exec(
        select(Location).where(
            Location.address == "Secret Street",
            Location.country == "France",
            Location.zip_code == "75000",
        )
    ).first()
    if not loc:
        loc = location_service.create_location(
            session,
            LocationCreate(address="Secret Street", country="France", zip_code="75000"),
        )

    # Check/Create Association
    asso_user = session.exec(
        select(User).where(User.email == "fake_asso@example.com")
    ).first()
    if not asso_user:
        asso = association_service.create_association(
            session,
            UserCreate(
                username="fake_asso",
                email="fake_asso@example.com",
                password=pwd,
                user_type=UserType.ASSOCIATION,
            ),
            AssociationCreate(
                name="Fake Association",
                rna_code="W000000000",
                phone_number="0100000000",
                company_name="Fake Corp",
                description="Nous ne sommes pas une vraie association.",
                address="1 Fake Street",
                zip_code="75000",
                country="France",
            ),
        )
        asso.verification_status = ProcessingStatus.APPROVED
        session.add(asso)
        session.flush()
    else:
        asso = session.exec(
            select(Association).where(Association.id_user == asso_user.id_user)
        ).first()
        if not asso:
            logger.warning(
                "User 'fake_asso@example.com' exists but Association row is missing. "
                "Skipping mission seeding."
            )

    # Check/Create Category
    existing_category = session.exec(
        select(Category).where(Category.label == "Test Category")
    ).first()
    if not existing_category:
        existing_category = Category(label="Test Category")
        session.add(existing_category)
        session.flush()

    category_id = existing_category.id_categ

    # Check/Create Mission
    if asso and loc:
        mission_exists = session.exec(
            select(Mission).where(
                Mission.name == "ARGENT FACILE ET RAPIDE",
                Mission.id_asso == asso.id_asso,
            )
        ).first()

        if not mission_exists:
            mission_service.create_mission(
                session,
                MissionCreate(
                    name="ARGENT FACILE ET RAPIDE",
                    description="Devenez riche en restant chez vous. Pas d'expérience requise. Offre limitée.",
                    id_asso=asso.id_asso,  # type: ignore
                    id_location=loc.id_location,  # type: ignore
                    category_ids=[category_id],
                    date_start=date.today(),
                    date_end=date.today(),
                    capacity_min=1,
                    capacity_max=100,
                    skills="Rien",
                ),
            )

    session.flush()
    logger.info("AI test data seeded successfully.")
