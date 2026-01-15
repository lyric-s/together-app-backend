"""Sample data initialization script for non-production environments.

This module seeds the database with realistic test data for development and staging.
Run automatically when ENVIRONMENT is 'development' or 'staging' during database initialization.

Features:
- Creates test users (volunteers, associations, admins)
- Sets up missions with engagements
- Creates documents and reports
- Generates notifications and badges
- All data is timestamped realistically
- Idempotent: Safe to run multiple times

Safety:
- Only runs in development and staging environments
- Checks if data already exists before creating
- Raises error if attempted in production
"""

from datetime import date, timedelta, datetime, timezone
from typing import Any, cast
from io import BytesIO
from sqlmodel import Session, select
from loguru import logger

from app.core.config import get_settings
from app.models.user import UserCreate, User
from app.models.volunteer import VolunteerCreate
from app.models.association import AssociationCreate
from app.models.mission import MissionCreate
from app.models.location import LocationCreate
from app.models.category import Category
from app.models.enums import UserType, ProcessingStatus, ReportType, ReportTarget
from app.models.engagement import Engagement
from app.models.report import ReportCreate
from app.models.document import Document
from app.models.favorite import Favorite
from app.models.notification import NotificationType, NotificationCreate
from app.models.badge import Badge
from app.models.assign import Assign
from app.services import volunteer as volunteer_service
from app.services import association as association_service
from app.services import mission as mission_service
from app.services import notification as notification_service
from app.services import report as report_service
from app.services import location as location_service
from app.services.storage import storage_service


def create_sample_pdf(document_name: str, association_name: str) -> BytesIO:
    """
    Create a simple sample PDF document for testing.

    Args:
        document_name: Name of the document
        association_name: Name of the association

    Returns:
        BytesIO: In-memory PDF file
    """
    # Create a minimal valid PDF structure
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 150
>>
stream
BT
/F1 24 Tf
50 700 Td
({document_name}) Tj
0 -30 Td
/F1 12 Tf
(Association: {association_name}) Tj
0 -20 Td
(This is a sample document for testing purposes.) Tj
0 -20 Td
(Generated automatically by the sample data script.) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
516
%%EOF
"""

    pdf_bytes = BytesIO(pdf_content.encode("latin-1"))
    pdf_bytes.seek(0)
    return pdf_bytes


def init_sample_data(session: Session) -> None:
    """
    Initialize sample data for non-production environments.

    Creates a comprehensive set of test data including users, missions, engagements,
    documents, and notifications for development and staging environments.

    This function is idempotent and safe to run multiple times. It will skip creation
    if sample data already exists.

    Safety guards:
    - Blocks execution in production environment
    - Checks for existing data before creating
    - Uses transactions for atomic operations

    Args:
        session: Database session for data creation

    Raises:
        RuntimeError: If attempted to run in production environment
    """
    # Safety guard: Block production environment
    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "Sample data initialization cannot run in production environment! "
            "This is a safety measure to prevent accidental data seeding in production."
        )

    # Idempotency check: Skip if data already exists
    if session.exec(select(User).where(User.email == "alice@example.com")).first():
        logger.info("Sample data already exists. Skipping initialization.")
        return

    logger.info(f"Initializing sample data for {settings.ENVIRONMENT} environment...")
    pwd = "password"
    today = date.today()
    now_utc = datetime.now(timezone.utc)

    # --- 1. Volunteers ---
    volunteers_config: list[dict[str, Any]] = [
        {
            "key": "alice",
            "user": {
                "username": "alice",
                "email": "alice@example.com",
                "password": pwd,
                "user_type": UserType.VOLUNTEER,
            },
            "profile": {
                "first_name": "Alice",
                "last_name": "Johnson",
                "phone_number": "0601010101",
                "birthdate": date(1990, 1, 1),
                "bio": "Loves nature and helping people.",
                "skills": "Gardening, First Aid",
                "address": "15 Rue de la Paix",
                "zip_code": "75002",
            },
        },
        {
            "key": "bob",
            "user": {
                "username": "bob",
                "email": "bob@example.com",
                "password": pwd,
                "user_type": UserType.VOLUNTEER,
            },
            "profile": {
                "first_name": "Bob",
                "last_name": "Smith",
                "phone_number": "0602020202",
                "birthdate": date(1985, 5, 20),
                "bio": "Can fix anything.",
                "skills": "Construction, Driving",
            },
        },
        {
            "key": "charlie",
            "user": {
                "username": "charlie",
                "email": "charlie@example.com",
                "password": pwd,
                "user_type": UserType.VOLUNTEER,
            },
            "profile": {
                "first_name": "Charlie",
                "last_name": "Brown",
                "phone_number": "0603030303",
                "birthdate": date(1995, 8, 15),
                "bio": "Silent but hard working.",
                "skills": "Entertainment, Cooking",
            },
        },
    ]

    volunteers = {}
    logger.info(f"Creating {len(volunteers_config)} Volunteers...")
    for v_conf in volunteers_config:
        vol = volunteer_service.create_volunteer(
            session,
            UserCreate(**cast(dict[str, Any], v_conf["user"])),
            VolunteerCreate(**cast(dict[str, Any], v_conf["profile"])),
        )
        volunteers[v_conf["key"]] = vol

    # --- 2. Associations ---
    associations_config: list[dict[str, Any]] = [
        {
            "key": "green_earth",
            "status": ProcessingStatus.APPROVED,
            "user": {
                "username": "greenearth",
                "email": "contact@greenearth.org",
                "password": pwd,
                "user_type": UserType.ASSOCIATION,
            },
            "profile": {
                "name": "Green Earth",
                "rna_code": "W123456789",
                "phone_number": "0102030405",
                "company_name": "Green Earth NGO",
                "description": "Protecting the planet one step at a time.",
                "address": "1 Earth Lane",
                "zip_code": "75001",
                "country": "France",
            },
        },
        {
            "key": "helping_hands",
            "status": ProcessingStatus.APPROVED,
            "user": {
                "username": "helpinghands",
                "email": "contact@helpinghands.org",
                "password": pwd,
                "user_type": UserType.ASSOCIATION,
            },
            "profile": {
                "name": "Helping Hands",
                "rna_code": "W987654321",
                "phone_number": "0504030201",
                "company_name": "Helping Hands Inc",
                "description": "Helping those in need with food and shelter.",
                "address": "2 Help Street",
                "zip_code": "69001",
                "country": "France",
            },
        },
        {
            "key": "tech_for_good",
            "status": ProcessingStatus.PENDING,
            "user": {
                "username": "techforgood",
                "email": "contact@techforgood.org",
                "password": pwd,
                "user_type": UserType.ASSOCIATION,
            },
            "profile": {
                "name": "Tech For Good",
                "rna_code": "W112233445",
                "phone_number": "0908070605",
                "company_name": "Tech For Good Assoc",
                "description": "Bridging the digital divide.",
                "address": "42 Silicon Blvd",
                "zip_code": "33000",
                "country": "France",
            },
        },
    ]

    associations = {}
    logger.info(f"Creating {len(associations_config)} Associations...")
    for a_conf in associations_config:
        asso = association_service.create_association(
            session,
            UserCreate(**cast(dict[str, Any], a_conf["user"])),
            AssociationCreate(**cast(dict[str, Any], a_conf["profile"])),
        )
        if a_conf["status"] == ProcessingStatus.APPROVED:
            asso.verification_status = ProcessingStatus.APPROVED
            session.add(asso)
        associations[a_conf["key"]] = asso
    session.flush()

    # --- 3. Categories & Locations ---
    logger.info("Fetching Categories...")
    categories = {}
    for label, key in [
        ("Biodiversité", "env"),
        ("Aide alimentaire", "social"),
        ("Mentorat", "mentor"),
    ]:
        cat = session.exec(select(Category).where(Category.label == label)).first()
        if cat:
            categories[key] = cat

    # Helper for fallback category list
    def get_cat_ids(key: str) -> list[int]:
        if key in categories:
            return [categories[key].id_categ]  # type: ignore
        # Fallback: return the first available category if specific key not found
        # This prevents "List should have at least 1 item" error
        if categories:
            return [next(iter(categories.values())).id_categ]  # type: ignore
        return []

    logger.info("Creating Locations...")
    locations_config: list[dict[str, Any]] = [
        {
            "key": "paris",
            "data": {
                "address": "Champ de Mars",
                "zip_code": "75007",
                "city": "Paris",
                "country": "France",
                "latitude": 48.855,
                "longitude": 2.299,
            },
        },
        {
            "key": "lyon",
            "data": {
                "address": "Place Bellecour",
                "zip_code": "69002",
                "city": "Lyon",
                "country": "France",
                "latitude": 45.757,
                "longitude": 4.832,
            },
        },
        {
            "key": "bordeaux",
            "data": {
                "address": "Place de la Bourse",
                "zip_code": "33000",
                "city": "Bordeaux",
                "country": "France",
                "latitude": 44.841,
                "longitude": -0.571,
            },
        },
    ]

    locations = {}
    for l_conf in locations_config:
        # Use LocationCreate + service for proper validation
        location_in = LocationCreate(**cast(dict[str, Any], l_conf["data"]))
        loc = location_service.create_location(session, location_in)
        locations[l_conf["key"]] = loc
    session.flush()

    # --- 4. Missions ---
    missions_config: list[dict[str, Any]] = [
        {
            "key": "cleanup_past",
            "asso": "green_earth",
            "loc": "paris",
            "cat": "env",
            "data": {
                "name": "Seine Cleanup 2023",
                "description": "Annual cleaning of the river banks. This mission is already finished.",
                "date_start": today - timedelta(days=365),
                "date_end": today - timedelta(days=360),
                "capacity_max": 50,
                "capacity_min": 5,
                "skills": "Swimming, Teamwork",
            },
        },
        {
            "key": "river_patrol",
            "asso": "green_earth",
            "loc": "paris",
            "cat": "env",
            "data": {
                "name": "River Patrol",
                "description": "Monitoring river pollution levels. Currently ongoing.",
                "date_start": today - timedelta(days=5),
                "date_end": today + timedelta(days=5),
                "capacity_max": 5,
                "capacity_min": 1,
                "skills": "Observation, Reporting",
            },
        },
        {
            "key": "tree_planting",
            "asso": "green_earth",
            "loc": "paris",
            "cat": "env",
            "data": {
                "name": "Urban Tree Planting",
                "description": "Planting trees in the city center. Open for volunteers.",
                "date_start": today + timedelta(days=20),
                "date_end": today + timedelta(days=25),
                "capacity_max": 20,
                "capacity_min": 5,
                "skills": "Digging, Strength",
            },
        },
        {
            "key": "soup_kitchen",
            "asso": "helping_hands",
            "loc": "lyon",
            "cat": "social",
            "data": {
                "name": "Soup Kitchen Gala",
                "description": "Serving food at the annual gala. High demand, nearly full.",
                "date_start": today + timedelta(days=10),
                "date_end": today + timedelta(days=10),
                "capacity_max": 3,
                "capacity_min": 1,
                "skills": "Cooking, Service",
            },
        },
        {
            "key": "coding",
            "asso": "tech_for_good",
            "loc": "bordeaux",
            "cat": "mentor",
            "data": {
                "name": "Coding for Seniors",
                "description": "Teaching basic coding skills to elderly people.",
                "date_start": today + timedelta(days=30),
                "date_end": today + timedelta(days=35),
                "capacity_max": 10,
                "capacity_min": 2,
                "skills": "Python, Patience",
            },
        },
    ]

    missions = {}
    logger.info(f"Creating {len(missions_config)} Missions...")
    for m_conf in missions_config:
        mission_in = MissionCreate(
            **cast(dict[str, Any], m_conf["data"]),
            id_asso=associations[m_conf["asso"]].id_asso,
            id_location=locations[m_conf["loc"]].id_location,  # type: ignore
            category_ids=get_cat_ids(cast(str, m_conf["cat"])),
        )
        mission = mission_service.create_mission(session, mission_in)
        missions[m_conf["key"]] = mission

    # --- 5. Engagements ---
    engagements_config: list[dict[str, Any]] = [
        {
            "vol": "alice",
            "mission": "cleanup_past",
            "state": ProcessingStatus.APPROVED,
            "date": today - timedelta(days=370),
        },
        {
            "vol": "alice",
            "mission": "river_patrol",
            "state": ProcessingStatus.APPROVED,
            "date": today - timedelta(days=10),
        },
        {
            "vol": "bob",
            "mission": "river_patrol",
            "state": ProcessingStatus.REJECTED,
            "reason": "Profile incomplete",
            "date": today - timedelta(days=2),
        },
        {
            "vol": "charlie",
            "mission": "soup_kitchen",
            "state": ProcessingStatus.PENDING,
            "message": "I would love to help!",
            "date": today,
        },
        {
            "vol": "alice",
            "mission": "soup_kitchen",
            "state": ProcessingStatus.APPROVED,
            "date": today - timedelta(days=5),
        },
        {
            "vol": "bob",
            "mission": "soup_kitchen",
            "state": ProcessingStatus.APPROVED,
            "date": today - timedelta(days=5),
        },
    ]

    logger.info(f"Creating {len(engagements_config)} Engagements...")
    for e_conf in engagements_config:
        engagement = Engagement(
            id_volunteer=volunteers[e_conf["vol"]].id_volunteer,
            id_mission=missions[e_conf["mission"]].id_mission,
            state=e_conf["state"],
            application_date=e_conf.get("date"),
            message=e_conf.get("message"),
            rejection_reason=e_conf.get("reason"),
        )
        session.add(engagement)

    # --- 6. Reports ---
    reports_config: list[dict[str, Any]] = [
        {
            "reporter": volunteers["alice"].id_user,
            "reported": associations["green_earth"].id_user,
            "type": ReportType.HARASSMENT,
            "target": ReportTarget.PROFILE,
            "reason": "Received rude messages after applying.",
            "date": now_utc - timedelta(days=2),
            "state": ProcessingStatus.PENDING,
        },
        {
            "reporter": associations["green_earth"].id_user,
            "reported": volunteers["bob"].id_user,
            "type": ReportType.FRAUD,
            "target": ReportTarget.PROFILE,
            "reason": "Volunteer claimed to have skills they do not possess.",
            "date": now_utc - timedelta(days=1),
            "state": ProcessingStatus.PENDING,
        },
        {
            "reporter": volunteers["bob"].id_user,
            "reported": volunteers["charlie"].id_user,
            "type": ReportType.SPAM,
            "target": ReportTarget.MESSAGE,
            "reason": "Sending repeated unsolicited messages.",
            "date": now_utc - timedelta(days=5),
            "state": ProcessingStatus.APPROVED,
        },
        {
            "reporter": volunteers["charlie"].id_user,
            "reported": associations["helping_hands"].id_user,
            "type": ReportType.INAPPROPRIATE_BEHAVIOR,
            "target": ReportTarget.MISSION,
            "reason": "Mission description contains inappropriate content.",
            "date": now_utc - timedelta(days=10),
            "state": ProcessingStatus.REJECTED,
        },
        {
            "reporter": associations["helping_hands"].id_user,
            "reported": volunteers["alice"].id_user,
            "type": ReportType.OTHER,
            "target": ReportTarget.PROFILE,
            "reason": "User did not show up for scheduled mission without notice.",
            "date": now_utc - timedelta(days=15),
            "state": ProcessingStatus.APPROVED,
        },
    ]

    logger.info(f"Creating {len(reports_config)} Reports...")
    for r_conf in reports_config:
        # Use ReportCreate + service for proper validation
        report_in = ReportCreate(
            type=r_conf["type"],
            target=r_conf["target"],
            reason=r_conf["reason"],
            id_user_reported=r_conf["reported"],
        )
        report = report_service.create_report(session, r_conf["reporter"], report_in)

        # Update state and date if not PENDING (service creates as PENDING by default)
        if r_conf["state"] != ProcessingStatus.PENDING:
            report.state = r_conf["state"]
        report.date_reporting = r_conf["date"]
        session.add(report)

    # --- 7. Documents ---
    # Ensure MinIO bucket exists before uploading
    storage_service.ensure_bucket_exists()

    documents_config: list[dict[str, Any]] = [
        {
            "asso": "green_earth",
            "name": "RNA Certificate 2023",
            "date": now_utc - timedelta(days=60),
            "state": ProcessingStatus.APPROVED,
        },
        {
            "asso": "green_earth",
            "name": "Liability Insurance 2025",
            "date": now_utc - timedelta(days=5),
            "state": ProcessingStatus.PENDING,
        },
        {
            "asso": "helping_hands",
            "name": "Association Statutes",
            "date": now_utc - timedelta(days=90),
            "state": ProcessingStatus.APPROVED,
        },
        {
            "asso": "helping_hands",
            "name": "Annual Report 2024",
            "date": now_utc - timedelta(days=3),
            "state": ProcessingStatus.PENDING,
        },
        {
            "asso": "tech_for_good",
            "name": "Registration Form",
            "date": now_utc - timedelta(days=1),
            "state": ProcessingStatus.PENDING,
        },
        {
            "asso": "tech_for_good",
            "name": "Board Minutes 2024",
            "date": now_utc - timedelta(days=15),
            "state": ProcessingStatus.REJECTED,
        },
    ]

    logger.info(f"Creating {len(documents_config)} Documents with MinIO uploads...")
    for d_conf in documents_config:
        # Get association name for PDF content
        asso_key = d_conf["asso"]
        asso_name = associations[asso_key].name

        # Create sample PDF
        pdf_file = create_sample_pdf(d_conf["name"], asso_name)

        # Upload to MinIO
        try:
            object_name = storage_service.upload_file(
                file_data=pdf_file,
                file_name=f"{d_conf['name']}.pdf",
                content_type="application/pdf",
                user_id=str(associations[asso_key].id_asso),
            )
            logger.debug(
                f"Uploaded document '{d_conf['name']}' to MinIO as '{object_name}'"
            )

            # Create document record with MinIO object name
            session.add(
                Document(
                    id_asso=associations[asso_key].id_asso,
                    doc_name=d_conf["name"],
                    url_doc=object_name,  # Store MinIO object name
                    date_upload=d_conf["date"],
                    verif_state=d_conf["state"],
                )
            )
        except Exception as e:
            logger.error(f"Failed to upload document '{d_conf['name']}': {e}")
            # Fallback to placeholder URL if upload fails
            session.add(
                Document(
                    id_asso=associations[asso_key].id_asso,
                    doc_name=d_conf["name"],
                    url_doc=f"placeholder_{d_conf['name']}.pdf",
                    date_upload=d_conf["date"],
                    verif_state=d_conf["state"],
                )
            )

    # --- 8. Favorites ---
    logger.info("Creating Favorites...")
    session.add(
        Favorite(
            id_volunteer=volunteers["alice"].id_volunteer,
            id_mission=missions["soup_kitchen"].id_mission,
            created_at=now_utc - timedelta(days=15),
        )
    )

    # --- 9. Badges ---
    logger.info("Creating Badges...")
    badges_config = [
        {"title": "Newcomer", "condition": 1, "reward": "Bronze Star"},
        {"title": "Expert Helper", "condition": 10, "reward": "Gold Medal"},
    ]

    badges = {}
    for b_conf in badges_config:
        badge = Badge(**b_conf)
        session.add(badge)
        badges[b_conf["title"]] = badge
    session.flush()

    # Assign Badge
    session.add(
        Assign(
            id_volunteer=volunteers["alice"].id_volunteer,
            id_badge=badges["Newcomer"].id_badge,
        )
    )

    # --- 10. Notifications ---
    logger.info("Creating Notifications...")
    notifications_config: list[dict[str, Any]] = [
        {
            "asso": "green_earth",
            "type": NotificationType.VOLUNTEER_JOINED,
            "msg": f"Volunteer {volunteers['alice'].first_name} joined River Patrol.",
            "mission": "river_patrol",
            "user": "alice",
            "read": False,
            "date": now_utc - timedelta(hours=2),
        },
        {
            "asso": "helping_hands",
            "type": NotificationType.CAPACITY_REACHED,
            "msg": "Mission Soup Kitchen Gala has reached maximum capacity.",
            "mission": "soup_kitchen",
            "user": None,
            "read": True,
            "date": now_utc - timedelta(minutes=30),
        },
    ]

    for n_conf in notifications_config:
        # Use NotificationCreate + service pattern for proper Pydantic validation
        notification_in = NotificationCreate(
            id_asso=associations[n_conf["asso"]].id_asso,
            notification_type=n_conf["type"],
            message=n_conf["msg"],
            related_mission_id=missions[n_conf["mission"]].id_mission,
            related_user_id=(
                volunteers[n_conf["user"]].id_user if n_conf["user"] else None
            ),
        )
        notification = notification_service.create_notification(
            session, notification_in
        )
        # Update ORM fields after creation (not part of NotificationCreate schema)
        notification.is_read = n_conf["read"]
        notification.created_at = n_conf["date"]
        session.add(notification)

    session.commit()
    logger.info(
        f"Sample data initialized successfully for {settings.ENVIRONMENT} environment"
    )
