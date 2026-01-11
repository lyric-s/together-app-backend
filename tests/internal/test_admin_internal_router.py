import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session
from fastapi.testclient import TestClient
from app.models.admin import AdminCreate
from app.services import admin as admin_service
from app.core.security import create_access_token
from app.models.association import Association
from app.models.document import Document
from app.models.user import UserCreate
from app.models.enums import UserType, ProcessingStatus
from app.services import user as user_service


@pytest.fixture(name="admin_token")
def admin_token_fixture(session: Session) -> str:
    admin_in = AdminCreate(
        username="admin_tester",
        email="admin_tester@example.com",
        password="password",
        first_name="Admin",
        last_name="Tester",
    )
    # Check if admin exists from other tests
    existing = admin_service.get_admin_by_username(session, "admin_tester")
    if not existing:
        admin = admin_service.create_admin(session, admin_in)
        session.commit()
    else:
        admin = existing

    return create_access_token(data={"sub": admin.username, "mode": "admin"})


@pytest.fixture(name="association_with_docs")
def association_with_docs_fixture(session: Session) -> Association:
    user_in = UserCreate(
        username="asso_docs",
        email="asso_docs@example.com",
        password="password",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_in)
    asso = Association(
        id_user=user.id_user,
        name="Asso Docs",
        rna_code="W999999999",
        company_name="Asso Docs Corp",
        phone_number="0102030405",
        address="123 Street",
        zip_code="75000",
        country="France",
        verification_status=ProcessingStatus.PENDING,
    )
    session.add(asso)
    session.commit()
    session.refresh(asso)

    # Create older document
    doc1 = Document(
        id_asso=asso.id_asso,
        doc_name="Old Doc",
        url_doc="old_url",
        verif_state=ProcessingStatus.REJECTED,
        date_upload=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add(doc1)

    # Create newer document
    doc2 = Document(
        id_asso=asso.id_asso,
        doc_name="New Doc",
        url_doc="new_url",
        verif_state=ProcessingStatus.PENDING,
        date_upload=datetime.now(timezone.utc),
    )
    session.add(doc2)
    session.commit()
    session.refresh(asso)
    return asso


def test_get_latest_association_document(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    response = client.get(
        f"/internal/admin/associations/{association_with_docs.id_asso}/documents/latest",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["doc_name"] == "New Doc"
    assert data["url_doc"] == "new_url"


def test_get_latest_association_document_not_found(
    client: TestClient, session: Session, admin_token: str
):
    non_existent_id = 99999
    response = client.get(
        f"/internal/admin/associations/{non_existent_id}/documents/latest",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
