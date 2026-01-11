"""Tests for document router endpoints."""

from unittest.mock import patch
import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient

from app.models.user import UserCreate
from app.models.enums import UserType, ProcessingStatus
from app.services import user as user_service
from app.models.association import Association
from app.models.document import Document

# Test constants
DOC_ASSO_USERNAME = "doc_asso"
DOC_ASSO_EMAIL = "doc@asso.com"
DOC_ASSO_PASSWORD = "Password123"
TEST_DOC_NAME = "Test Document"
TEST_FILE_CONTENT = b"fake pdf content"
TEST_FILE_NAME = "test.pdf"


@pytest.fixture(name="doc_asso")
def doc_asso_fixture(session: Session):
    """Create an association for document testing."""
    user_in = UserCreate(
        username=DOC_ASSO_USERNAME,
        email=DOC_ASSO_EMAIL,
        password=DOC_ASSO_PASSWORD,
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_in)
    asso = Association(
        id_user=user.id_user,
        name="Doc Asso",
        rna_code="W123456789",
        company_name="Doc Corp",
        phone_number="0102030405",
        address="Doc Street",
        zip_code="75000",
        country="France",
    )
    session.add(asso)
    session.commit()
    session.refresh(asso)
    return asso


@pytest.fixture(name="doc_token")
def doc_token_fixture(doc_asso):
    """Generate valid JWT token for doc_asso."""
    from app.core.security import create_access_token

    return create_access_token(data={"sub": DOC_ASSO_USERNAME})


class TestDocumentOperations:
    """Test document lifecycle: upload, retrieve, download, and delete."""

    def test_upload_document_success(self, client: TestClient, doc_token):
        """Upload a document file and verify its storage URL and record creation."""
        with patch("app.services.storage.storage_service.upload_file") as mock_upload:
            mock_upload.return_value = "uploaded_object_key"

            response = client.post(
                "/documents/upload",
                headers={"Authorization": f"Bearer {doc_token}"},
                data={"doc_name": TEST_DOC_NAME},
                files={"file": (TEST_FILE_NAME, TEST_FILE_CONTENT, "application/pdf")},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["doc_name"] == TEST_DOC_NAME
            assert data["url_doc"] == "uploaded_object_key"
            assert data["verif_state"] == ProcessingStatus.PENDING.value
            mock_upload.assert_called_once()

    def test_read_my_documents(
        self, session: Session, client: TestClient, doc_asso, doc_token
    ):
        """Retrieve a list of documents belonging to the authenticated association."""
        # Setup: Pre-create a document record
        doc = Document(
            id_asso=doc_asso.id_asso,
            doc_name=TEST_DOC_NAME,
            url_doc="stored_key",
            verification_status=ProcessingStatus.PENDING,
        )
        session.add(doc)
        session.commit()

        response = client.get(
            "/documents/me", headers={"Authorization": f"Bearer {doc_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["doc_name"] == TEST_DOC_NAME

    def test_get_document_download_url(
        self, session: Session, client: TestClient, doc_asso, doc_token
    ):
        """Generate a presigned download URL for a specific document."""
        doc = Document(
            id_asso=doc_asso.id_asso,
            doc_name="Downloadable Doc",
            url_doc="key_to_download",
            verification_status=ProcessingStatus.APPROVED,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        with patch(
            "app.services.storage.storage_service.get_presigned_url"
        ) as mock_url:
            mock_url.return_value = "http://minio-server/key_to_download?signature=abc"

            response = client.get(
                f"/documents/{doc.id_doc}/download-url",
                headers={"Authorization": f"Bearer {doc_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert (
                data["download_url"]
                == "http://minio-server/key_to_download?signature=abc"
            )
            mock_url.assert_called_once_with("key_to_download")

    def test_delete_document_success(
        self, session: Session, client: TestClient, doc_asso, doc_token
    ):
        """Permanently delete a document record and its associated storage file."""
        doc = Document(
            id_asso=doc_asso.id_asso, doc_name="To be deleted", url_doc="key_to_delete"
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.id_doc

        with patch("app.services.storage.storage_service.delete_file") as mock_delete:
            response = client.delete(
                f"/documents/{doc_id}", headers={"Authorization": f"Bearer {doc_token}"}
            )

            assert response.status_code == 204
            # Verify database record is gone
            session.expire_all()
            assert session.get(Document, doc_id) is None
            mock_delete.assert_called_once_with("key_to_delete")
