import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session
from fastapi.testclient import TestClient
from unittest.mock import patch
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


# Document URL endpoint tests


def test_get_document_download_url_success(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    """Test successful generation of document download URL."""
    # Get the first document from the association
    document = association_with_docs.documents[0]

    with patch(
        "app.services.storage.storage_service.get_presigned_url"
    ) as mock_presigned:
        mock_presigned.return_value = (
            "http://minio:9000/bucket/file.pdf?signature=abc123"
        )

        response = client.get(
            f"/internal/admin/documents/{document.id_doc}/download-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert "expires_in" in data
        assert (
            data["download_url"] == "http://minio:9000/bucket/file.pdf?signature=abc123"
        )
        assert data["expires_in"] == 3600

        # Verify storage service was called with inline=False
        mock_presigned.assert_called_once_with(document.url_doc, inline=False)


def test_get_document_download_url_not_found(
    client: TestClient, session: Session, admin_token: str
):
    """Test download URL endpoint returns 404 for nonexistent document."""
    non_existent_id = 99999
    response = client.get(
        f"/internal/admin/documents/{non_existent_id}/download-url",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_get_document_download_url_storage_failure(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    """Test download URL endpoint raises error when storage service fails."""
    document = association_with_docs.documents[0]

    with patch(
        "app.services.storage.storage_service.get_presigned_url"
    ) as mock_presigned:
        # Simulate storage service failure (returns None)
        mock_presigned.return_value = None

        response = client.get(
            f"/internal/admin/documents/{document.id_doc}/download-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 422  # ValidationError
        data = response.json()
        assert "detail" in data
        assert "Failed to generate download URL" in data["detail"]


def test_get_document_download_url_unauthorized(
    client: TestClient, session: Session, association_with_docs: Association
):
    """Test download URL endpoint requires admin authentication."""
    document = association_with_docs.documents[0]

    response = client.get(
        f"/internal/admin/documents/{document.id_doc}/download-url",
        # No authorization header
    )
    assert response.status_code == 401


def test_get_document_preview_url_success(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    """Test successful generation of document preview URL."""
    document = association_with_docs.documents[0]

    with patch(
        "app.services.storage.storage_service.get_presigned_url"
    ) as mock_presigned:
        mock_presigned.return_value = "http://minio:9000/bucket/file.pdf?response-content-disposition=inline&sig=xyz"

        response = client.get(
            f"/internal/admin/documents/{document.id_doc}/preview-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "preview_url" in data
        assert "expires_in" in data
        assert "response-content-disposition=inline" in data["preview_url"]
        assert data["expires_in"] == 3600

        # Verify storage service was called with inline=True
        mock_presigned.assert_called_once_with(document.url_doc, inline=True)


def test_get_document_preview_url_not_found(
    client: TestClient, session: Session, admin_token: str
):
    """Test preview URL endpoint returns 404 for nonexistent document."""
    non_existent_id = 99999
    response = client.get(
        f"/internal/admin/documents/{non_existent_id}/preview-url",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


def test_get_document_preview_url_storage_failure(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    """Test preview URL endpoint raises error when storage service fails."""
    document = association_with_docs.documents[0]

    with patch(
        "app.services.storage.storage_service.get_presigned_url"
    ) as mock_presigned:
        # Simulate storage service failure (returns None)
        mock_presigned.return_value = None

        response = client.get(
            f"/internal/admin/documents/{document.id_doc}/preview-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 422  # ValidationError
        data = response.json()
        assert "detail" in data
        assert "Failed to generate preview URL" in data["detail"]


def test_get_document_preview_url_unauthorized(
    client: TestClient, session: Session, association_with_docs: Association
):
    """Test preview URL endpoint requires admin authentication."""
    document = association_with_docs.documents[0]

    response = client.get(
        f"/internal/admin/documents/{document.id_doc}/preview-url",
        # No authorization header
    )
    assert response.status_code == 401


def test_download_vs_preview_url_different_modes(
    client: TestClient,
    session: Session,
    admin_token: str,
    association_with_docs: Association,
):
    """Test that download and preview endpoints call storage service with different modes."""
    document = association_with_docs.documents[0]

    with patch(
        "app.services.storage.storage_service.get_presigned_url"
    ) as mock_presigned:
        mock_presigned.return_value = "http://minio:9000/bucket/file.pdf"

        # Call download endpoint
        client.get(
            f"/internal/admin/documents/{document.id_doc}/download-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        download_call = mock_presigned.call_args

        # Reset mock and call preview endpoint
        mock_presigned.reset_mock()
        client.get(
            f"/internal/admin/documents/{document.id_doc}/preview-url",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        preview_call = mock_presigned.call_args

        # Verify different inline parameter values
        assert download_call.kwargs["inline"] is False
        assert preview_call.kwargs["inline"] is True
