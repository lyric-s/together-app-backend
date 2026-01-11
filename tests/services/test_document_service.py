"""Tests for document service CRUD operations and validation workflow."""

import pytest
from sqlmodel import Session
from unittest.mock import patch

from app.models.user import UserCreate
from app.models.admin import Admin, AdminCreate
from app.models.association import Association, AssociationCreate
from app.models.document import Document, DocumentCreate, DocumentUpdate
from app.models.enums import UserType, ProcessingStatus
from app.services import document as document_service
from app.services import association as association_service
from app.services import admin as admin_service
from app.exceptions import NotFoundError, ValidationError, InsufficientPermissionsError

# Test data constants
TEST_DOC_NAME = "RNA Registration Certificate"
TEST_DOC_URL = "documents/test-certificate.pdf"
TEST_REJECTION_REASON = "Document is not clear enough"
NONEXISTENT_ID = 99999


@pytest.fixture(name="sample_association")
def sample_association_fixture(session: Session) -> Association:
    """Create a test association with user."""
    user_create = UserCreate(
        username="test_asso_user",
        email="test_asso@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    asso_create = AssociationCreate(
        name="Test Association",
        address="123 Test Street",
        country="France",
        phone_number="+33123456789",
        zip_code="75001",
        rna_code="W123456789",
        company_name="Test Association Company",
        description="Test Description",
    )
    return association_service.create_association(session, user_create, asso_create)


@pytest.fixture(name="sample_admin")
def sample_admin_fixture(session: Session) -> Admin:
    """Create a test admin."""
    admin_create = AdminCreate(
        username="test_admin",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        password="AdminPass123",
    )
    return admin_service.create_admin(session, admin_create)


@pytest.fixture(name="sample_document_create")
def sample_document_create_fixture() -> DocumentCreate:
    """Provide a standard DocumentCreate object."""
    return DocumentCreate(
        doc_name=TEST_DOC_NAME,
        url_doc=TEST_DOC_URL,
        id_asso=1,  # Will be overridden
    )


@pytest.fixture(name="created_document")
def created_document_fixture(
    session: Session,
    sample_association: Association,
    sample_document_create: DocumentCreate,
) -> Document:
    """Create a document for testing."""
    assert sample_association.id_asso is not None
    return document_service.create_document(
        session, sample_document_create, sample_association.id_asso
    )


@pytest.fixture(name="document_factory")
def document_factory_fixture(session: Session, sample_association: Association):
    """Provide a factory for creating test documents."""

    def _create_document(index: int = 0, **overrides) -> Document:
        """
        Create and persist a Document test record.

        Parameters:
            index (int): Numeric suffix for unique document names.
            **overrides: Field names and values to override defaults.

        Returns:
            Document: The created Document instance.
        """
        assert sample_association.id_asso is not None
        data = {
            "doc_name": f"Document {index}",
            "url_doc": f"documents/doc_{index}.pdf",
            "id_asso": sample_association.id_asso,
        }
        data.update(overrides)
        doc_create = DocumentCreate(**data)
        return document_service.create_document(
            session, doc_create, sample_association.id_asso
        )

    return _create_document


class TestCreateDocument:
    """Test document creation."""

    def test_create_document_success(
        self, session: Session, sample_association: Association
    ):
        """Test successful document creation."""
        doc_create = DocumentCreate(
            doc_name=TEST_DOC_NAME,
            url_doc=TEST_DOC_URL,
            id_asso=sample_association.id_asso,
        )
        assert sample_association.id_asso is not None
        document = document_service.create_document(
            session, doc_create, sample_association.id_asso
        )

        assert document.id_doc is not None
        assert document.doc_name == TEST_DOC_NAME
        assert document.url_doc == TEST_DOC_URL
        assert document.id_asso == sample_association.id_asso
        assert document.verif_state == ProcessingStatus.PENDING
        assert document.id_admin is None
        assert document.rejection_reason is None

    def test_create_document_association_not_found(
        self, session: Session, sample_document_create: DocumentCreate
    ):
        """Test document creation with non-existent association."""
        with pytest.raises(NotFoundError) as exc_info:
            document_service.create_document(
                session, sample_document_create, NONEXISTENT_ID
            )
        assert "Association" in str(exc_info.value)

    def test_create_document_defaults(
        self, session: Session, created_document: Document
    ):
        """Test that document defaults are set correctly."""
        assert created_document.verif_state == ProcessingStatus.PENDING
        assert created_document.id_admin is None
        assert created_document.date_upload is not None


class TestGetDocument:
    """Test document retrieval."""

    def test_get_document_by_id(self, session: Session, created_document: Document):
        """Test retrieving document by ID."""
        assert created_document.id_doc is not None
        fetched = document_service.get_document(session, created_document.id_doc)

        assert fetched is not None
        assert fetched.id_doc == created_document.id_doc
        assert fetched.doc_name == TEST_DOC_NAME

    def test_get_document_not_found(self, session: Session):
        """Test retrieving non-existent document."""
        assert document_service.get_document(session, NONEXISTENT_ID) is None

    def test_get_documents_by_association(
        self, session: Session, sample_association: Association, document_factory
    ):
        """Test retrieving all documents for an association."""
        # Create multiple documents
        doc1 = document_factory(1)
        doc2 = document_factory(2)

        assert sample_association.id_asso is not None
        documents = document_service.get_documents_by_association(
            session, sample_association.id_asso
        )

        assert len(documents) == 2
        doc_ids = [d.id_doc for d in documents]
        assert doc1.id_doc in doc_ids
        assert doc2.id_doc in doc_ids

    def test_get_documents_by_association_empty(
        self, session: Session, sample_association: Association
    ):
        """Test retrieving documents for association with no documents."""
        assert sample_association.id_asso is not None
        documents = document_service.get_documents_by_association(
            session, sample_association.id_asso
        )
        assert len(documents) == 0


class TestGetPendingDocuments:
    """Test pending documents retrieval."""

    def test_get_pending_documents(self, session: Session, document_factory):
        """Test retrieving pending documents."""

        # Create documents with different statuses

        pending_doc = document_factory(1)

        assert pending_doc.verif_state == ProcessingStatus.PENDING

        pending_docs = document_service.get_pending_documents(session)

        assert len(pending_docs) >= 1

        assert any(d.id_doc == pending_doc.id_doc for d in pending_docs)

    @pytest.mark.asyncio
    async def test_get_pending_documents_excludes_non_pending(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test that approved/rejected documents are excluded from pending list."""

        # Approve the document

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        await document_service.approve_document(
            session, created_document.id_doc, sample_admin.id_admin
        )

        # Check pending documents

        pending_docs = document_service.get_pending_documents(session)

        assert not any(d.id_doc == created_document.id_doc for d in pending_docs)


class TestUpdateDocument:
    """Test document updates."""

    def test_update_document_name(self, session: Session, created_document: Document):
        """Test updating document name."""

        assert created_document.id_doc is not None

        new_name = "Updated Certificate Name"

        update_data = DocumentUpdate(doc_name=new_name)

        updated = document_service.update_document(
            session, created_document.id_doc, update_data
        )

        assert updated.doc_name == new_name

        assert updated.url_doc == TEST_DOC_URL  # Unchanged

    def test_update_document_not_found(self, session: Session):
        """Test updating non-existent document."""

        with pytest.raises(NotFoundError):
            document_service.update_document(
                session, NONEXISTENT_ID, DocumentUpdate(doc_name="New Name")
            )


class TestApproveDocument:
    """Test document approval workflow."""

    @pytest.mark.asyncio
    async def test_approve_document_success(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test successful document approval."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        approved = await document_service.approve_document(
            session, created_document.id_doc, sample_admin.id_admin
        )

        assert approved.verif_state == ProcessingStatus.APPROVED

        assert approved.id_admin == sample_admin.id_admin

        assert approved.rejection_reason is None

    @pytest.mark.asyncio
    async def test_approve_document_updates_association_status(
        self,
        session: Session,
        created_document: Document,
        sample_admin: Admin,
        sample_association: Association,
    ):
        """Test that approving document updates association verification status."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        # Verify association starts as PENDING

        assert sample_association.verification_status == ProcessingStatus.PENDING

        # Approve document

        await document_service.approve_document(
            session, created_document.id_doc, sample_admin.id_admin
        )

        # Check association status updated

        assert sample_association.id_asso is not None

        updated_asso = association_service.get_association(
            session, sample_association.id_asso
        )

        assert updated_asso is not None

        assert updated_asso.verification_status == ProcessingStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_document_not_pending_fails(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test that approving already approved document fails."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        # Approve once

        await document_service.approve_document(
            session, created_document.id_doc, sample_admin.id_admin
        )

        # Try to approve again

        with pytest.raises(ValidationError) as exc_info:
            await document_service.approve_document(
                session, created_document.id_doc, sample_admin.id_admin
            )

        assert "Only PENDING documents can be approved" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_approve_document_not_found(
        self, session: Session, sample_admin: Admin
    ):
        """Test approving non-existent document."""

        assert sample_admin.id_admin is not None

        with pytest.raises(NotFoundError):
            await document_service.approve_document(
                session, NONEXISTENT_ID, sample_admin.id_admin
            )


class TestRejectDocument:
    """Test document rejection workflow."""

    @pytest.mark.asyncio
    async def test_reject_document_success(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test successful document rejection."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        rejected = await document_service.reject_document(
            session,
            created_document.id_doc,
            sample_admin.id_admin,
            TEST_REJECTION_REASON,
        )

        assert rejected.verif_state == ProcessingStatus.REJECTED

        assert rejected.id_admin == sample_admin.id_admin

        assert rejected.rejection_reason == TEST_REJECTION_REASON

    @pytest.mark.asyncio
    async def test_reject_document_without_reason(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test rejecting document without providing reason."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        rejected = await document_service.reject_document(
            session, created_document.id_doc, sample_admin.id_admin, None
        )

        assert rejected.verif_state == ProcessingStatus.REJECTED

        assert rejected.rejection_reason is None

    @pytest.mark.asyncio
    async def test_reject_document_updates_association_status(
        self,
        session: Session,
        created_document: Document,
        sample_admin: Admin,
        sample_association: Association,
    ):
        """Test that rejecting document updates association verification status."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        # Reject document

        await document_service.reject_document(
            session,
            created_document.id_doc,
            sample_admin.id_admin,
            TEST_REJECTION_REASON,
        )

        # Check association status updated

        assert sample_association.id_asso is not None

        updated_asso = association_service.get_association(
            session, sample_association.id_asso
        )

        assert updated_asso is not None

        assert updated_asso.verification_status == ProcessingStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_document_not_pending_fails(
        self, session: Session, created_document: Document, sample_admin: Admin
    ):
        """Test that rejecting already rejected document fails."""

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        # Reject once

        await document_service.reject_document(
            session,
            created_document.id_doc,
            sample_admin.id_admin,
            TEST_REJECTION_REASON,
        )

        # Try to reject again

        with pytest.raises(ValidationError) as exc_info:
            await document_service.reject_document(
                session,
                created_document.id_doc,
                sample_admin.id_admin,
                "Another reason",
            )

        assert "Only PENDING documents can be rejected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reject_document_not_found(
        self, session: Session, sample_admin: Admin
    ):
        """Test rejecting non-existent document."""

        assert sample_admin.id_admin is not None

        with pytest.raises(NotFoundError):
            await document_service.reject_document(
                session, NONEXISTENT_ID, sample_admin.id_admin, TEST_REJECTION_REASON
            )


class TestDeleteDocument:
    """Test document deletion."""

    @patch("app.services.document.storage_service")
    def test_delete_document_success(
        self, mock_storage, session: Session, created_document: Document
    ):
        """Test successful document deletion."""

        assert created_document.id_doc is not None

        doc_id = created_document.id_doc

        document_service.delete_document(session, doc_id)

        # Verify document deleted from database

        assert document_service.get_document(session, doc_id) is None

        # Verify storage deletion was attempted

        mock_storage.delete_file.assert_called_once_with(TEST_DOC_URL)

    @patch("app.services.document.storage_service")
    def test_delete_document_storage_failure_continues(
        self, mock_storage, session: Session, created_document: Document
    ):
        """Test that deletion continues even if storage fails."""

        mock_storage.delete_file.side_effect = Exception("Storage error")

        assert created_document.id_doc is not None

        doc_id = created_document.id_doc

        # Should not raise exception

        document_service.delete_document(session, doc_id)

        # Document should still be deleted from database

        assert document_service.get_document(session, doc_id) is None

    def test_delete_document_not_found(self, session: Session):
        """Test deleting non-existent document."""

        with pytest.raises(NotFoundError):
            document_service.delete_document(session, NONEXISTENT_ID)


class TestVerifyDocumentOwnership:
    """Test document ownership verification."""

    def test_verify_ownership_success(
        self,
        session: Session,
        created_document: Document,
        sample_association: Association,
    ):
        """Test successful ownership verification."""

        assert sample_association.id_asso is not None

        # Should not raise exception

        document_service.verify_document_ownership(
            created_document, sample_association.id_asso
        )

    def test_verify_ownership_fails(self, session: Session, created_document: Document):
        """Test ownership verification failure."""

        wrong_asso_id = 999

        with pytest.raises(InsufficientPermissionsError) as exc_info:
            document_service.verify_document_ownership(created_document, wrong_asso_id)

        assert "access this document" in str(exc_info.value)


class TestCanAssociationCreateMissions:
    """Test association mission creation permission check."""

    def test_can_create_missions_pending(
        self, session: Session, sample_association: Association
    ):
        """Test that pending associations cannot create missions."""

        assert sample_association.id_asso is not None

        assert sample_association.verification_status == ProcessingStatus.PENDING

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is False

    @pytest.mark.asyncio
    async def test_can_create_missions_approved(
        self,
        session: Session,
        sample_association: Association,
        created_document: Document,
        sample_admin: Admin,
    ):
        """Test that approved associations can create missions."""

        # Approve document

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        await document_service.approve_document(
            session, created_document.id_doc, sample_admin.id_admin
        )

        # Check permission

        assert sample_association.id_asso is not None

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is True

    @pytest.mark.asyncio
    async def test_can_create_missions_rejected(
        self,
        session: Session,
        sample_association: Association,
        created_document: Document,
        sample_admin: Admin,
    ):
        """Test that rejected associations cannot create missions."""

        # Reject document

        assert created_document.id_doc is not None

        assert sample_admin.id_admin is not None

        await document_service.reject_document(
            session,
            created_document.id_doc,
            sample_admin.id_admin,
            TEST_REJECTION_REASON,
        )

        # Check permission

        assert sample_association.id_asso is not None

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is False

    def test_can_create_missions_nonexistent_association(self, session: Session):
        """Test permission check for non-existent association."""

        can_create = document_service.can_association_create_missions(
            session, NONEXISTENT_ID
        )

        assert can_create is False


class TestDocumentWorkflowIntegration:
    """Test complete document validation workflow."""

    @pytest.mark.asyncio
    async def test_complete_approval_workflow(
        self,
        session: Session,
        sample_association: Association,
        sample_admin: Admin,
    ):
        """Test complete workflow from document creation to approval."""

        # 1. Association starts as PENDING

        assert sample_association.verification_status == ProcessingStatus.PENDING

        assert sample_association.id_asso is not None

        # 2. Association uploads document

        doc_create = DocumentCreate(
            doc_name="RNA Certificate",
            url_doc="documents/rna.pdf",
            id_asso=sample_association.id_asso,
        )

        document = document_service.create_document(
            session, doc_create, sample_association.id_asso
        )

        assert document.verif_state == ProcessingStatus.PENDING

        # 3. Admin retrieves pending documents

        pending_docs = document_service.get_pending_documents(session)

        assert any(d.id_doc == document.id_doc for d in pending_docs)

        # 4. Admin approves document

        assert document.id_doc is not None

        assert sample_admin.id_admin is not None

        approved_doc = await document_service.approve_document(
            session, document.id_doc, sample_admin.id_admin
        )

        assert approved_doc.verif_state == ProcessingStatus.APPROVED

        # 5. Association status is updated

        updated_asso = association_service.get_association(
            session, sample_association.id_asso
        )

        assert updated_asso is not None

        assert updated_asso.verification_status == ProcessingStatus.APPROVED

        # 6. Association can now create missions

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is True

    @pytest.mark.asyncio
    async def test_complete_rejection_workflow(
        self,
        session: Session,
        sample_association: Association,
        sample_admin: Admin,
    ):
        """Test complete workflow from document creation to rejection."""

        # 1. Association uploads document

        assert sample_association.id_asso is not None

        doc_create = DocumentCreate(
            doc_name="Invalid Document",
            url_doc="documents/invalid.pdf",
            id_asso=sample_association.id_asso,
        )

        document = document_service.create_document(
            session, doc_create, sample_association.id_asso
        )

        # 2. Admin rejects document with reason

        assert document.id_doc is not None

        assert sample_admin.id_admin is not None

        rejected_doc = await document_service.reject_document(
            session, document.id_doc, sample_admin.id_admin, "Document is expired"
        )

        assert rejected_doc.verif_state == ProcessingStatus.REJECTED

        assert rejected_doc.rejection_reason == "Document is expired"

        # 3. Association status is updated

        updated_asso = association_service.get_association(
            session, sample_association.id_asso
        )

        assert updated_asso is not None

        assert updated_asso.verification_status == ProcessingStatus.REJECTED

        # 4. Association cannot create missions

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is False

        # 5. Association can upload new document

        new_doc_create = DocumentCreate(
            doc_name="New Valid Document",
            url_doc="documents/valid_new.pdf",
            id_asso=sample_association.id_asso,
        )

        new_document = document_service.create_document(
            session, new_doc_create, sample_association.id_asso
        )

        assert new_document.verif_state == ProcessingStatus.PENDING

        # 6. Admin approves new document

        assert new_document.id_doc is not None

        await document_service.approve_document(
            session, new_document.id_doc, sample_admin.id_admin
        )

        # 7. Association can now create missions

        can_create = document_service.can_association_create_missions(
            session, sample_association.id_asso
        )

        assert can_create is True
