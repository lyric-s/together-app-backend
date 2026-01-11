"""Document service module for CRUD operations and validation workflow."""

import logging
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentCreate, DocumentUpdate
from app.models.enums import ProcessingStatus
from app.exceptions import NotFoundError, ValidationError, InsufficientPermissionsError
from app.services.storage import storage_service
from app.services import association as association_service
from app.services.email import send_notification_email


def create_document(
    session: Session, document_in: DocumentCreate, association_id: int
) -> Document:
    """
    Create a new document for an association.

    Parameters:
        session: Database session.
        document_in: Document creation data including file URL and name.
        association_id: The association submitting the document.

    Returns:
        Document: The created document record.

    Raises:
        NotFoundError: If the association doesn't exist.
    """
    # Verify association exists
    association = association_service.get_association(session, association_id)
    if not association:
        raise NotFoundError("Association", association_id)

    # Create document with explicit association ID
    db_document = Document.model_validate(
        document_in,
        update={
            "id_asso": association_id,
            "verif_state": ProcessingStatus.PENDING,
            "id_admin": None,
        },
    )

    session.add(db_document)
    session.flush()
    session.refresh(db_document)

    return db_document


def get_document(session: Session, document_id: int) -> Document | None:
    """
    Retrieve a document by ID with relationships loaded.

    Parameters:
        session: Database session.
        document_id: The document's primary key.

    Returns:
        Document | None: The document record, or None if not found.
    """
    statement = (
        select(Document)
        .where(Document.id_doc == document_id)
        .options(
            selectinload(Document.association),  # type: ignore
            selectinload(Document.admin),  # type: ignore
        )
    )
    return session.exec(statement).first()


def get_documents_by_association(
    session: Session, association_id: int
) -> list[Document]:
    """
    Retrieve all documents for a specific association.

    Parameters:
        session: Database session.
        association_id: The association's ID.

    Returns:
        list[Document]: List of documents belonging to the association.
    """
    statement = (
        select(Document)
        .where(Document.id_asso == association_id)
        .order_by(Document.date_upload.desc())  # type: ignore
    )
    return list(session.exec(statement).all())


def get_all_documents(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[Document]:
    """
    Retrieve all documents (admin function).

    Parameters:
        session: Database session.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[Document]: All documents, ordered by most recent first.
    """
    statement = (
        select(Document)
        .options(
            selectinload(Document.association),  # type: ignore
            selectinload(Document.admin),  # type: ignore
        )
        .order_by(Document.date_upload.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_pending_documents(session: Session) -> list[Document]:
    """
    Retrieve all documents with PENDING verification status.

    Used by admins to see which documents need review.

    Parameters:
        session: Database session.

    Returns:
        list[Document]: List of pending documents with association details loaded.
    """
    statement = (
        select(Document)
        .where(Document.verif_state == ProcessingStatus.PENDING)
        .options(selectinload(Document.association))  # type: ignore
        .order_by(Document.date_upload.asc())  # type: ignore - Oldest first (FIFO)
    )
    return list(session.exec(statement).all())


def update_document(
    session: Session, document_id: int, document_update: DocumentUpdate
) -> Document:
    """
    Update a document's information.

    Parameters:
        session: Database session.
        document_id: Primary key of the document to update.
        document_update: Partial update data.

    Returns:
        Document: The updated document record.

    Raises:
        NotFoundError: If no document exists with the given ID.
    """
    db_document = get_document(session, document_id)
    if not db_document:
        raise NotFoundError("Document", document_id)

    # Convert update model to dict, excluding unset fields
    update_data = document_update.model_dump(exclude_unset=True)

    # Update document fields
    for key, value in update_data.items():
        setattr(db_document, key, value)

    session.add(db_document)
    session.flush()
    session.refresh(db_document)

    return db_document


async def approve_document(
    session: Session, document_id: int, admin_id: int
) -> Document:
    """
    Approve a document and update the associated association's verification status.

    This is the primary workflow for document validation. When a document is approved:
    1. Document status is set to APPROVED
    2. Admin ID is recorded
    3. Association's verification_status is set to APPROVED
    4. Association can now create missions
    5. Email notification is sent to the association

    Parameters:
        session: Database session.
        document_id: The document to approve.
        admin_id: The admin performing the approval.

    Returns:
        Document: The approved document.

    Raises:
        NotFoundError: If document doesn't exist.
        ValidationError: If document is not in PENDING state.
    """
    db_document = get_document(session, document_id)
    if not db_document:
        raise NotFoundError("Document", document_id)

    # Validate document is pending
    if db_document.verif_state != ProcessingStatus.PENDING:
        raise ValidationError(
            f"Cannot approve document with status {db_document.verif_state}. "
            "Only PENDING documents can be approved.",
            field="verif_state",
        )

    # Update document status
    db_document.verif_state = ProcessingStatus.APPROVED
    db_document.id_admin = admin_id
    db_document.rejection_reason = None  # Clear any previous rejection reason

    # Update association verification status
    association = association_service.get_association(session, db_document.id_asso)
    if association:
        association.verification_status = ProcessingStatus.APPROVED
        session.add(association)

    session.add(db_document)
    session.flush()
    session.refresh(db_document)

    # Send email notification to association
    if association and association.user:
        try:
            await send_notification_email(
                template_name="document_approved",
                recipient_email=association.user.email,
                context={"association_name": association.name},
            )
        except Exception as e:
            # Log error but don't fail the operation
            logging.error(f"Failed to send document approval email: {e}")

    return db_document


async def reject_document(
    session: Session,
    document_id: int,
    admin_id: int,
    rejection_reason: str | None = None,
) -> Document:
    """
    Reject a document and update the associated association's verification status.

    When a document is rejected:
    1. Document status is set to REJECTED
    2. Admin ID is recorded
    3. Rejection reason is stored (if provided)
    4. Association's verification_status is set to REJECTED
    5. Association cannot create missions until a new document is approved
    6. Email notification is sent to the association

    Parameters:
        session: Database session.
        document_id: The document to reject.
        admin_id: The admin performing the rejection.
        rejection_reason: Optional explanation for rejection.

    Returns:
        Document: The rejected document.

    Raises:
        NotFoundError: If document doesn't exist.
        ValidationError: If document is not in PENDING state.
    """
    db_document = get_document(session, document_id)
    if not db_document:
        raise NotFoundError("Document", document_id)

    # Validate document is pending
    if db_document.verif_state != ProcessingStatus.PENDING:
        raise ValidationError(
            f"Cannot reject document with status {db_document.verif_state}. "
            "Only PENDING documents can be rejected.",
            field="verif_state",
        )

    # Update document status
    db_document.verif_state = ProcessingStatus.REJECTED
    db_document.id_admin = admin_id
    db_document.rejection_reason = rejection_reason

    # Update association verification status
    association = association_service.get_association(session, db_document.id_asso)
    if association:
        association.verification_status = ProcessingStatus.REJECTED
        session.add(association)

    session.add(db_document)
    session.flush()
    session.refresh(db_document)

    # Send email notification to association
    if association and association.user:
        try:
            await send_notification_email(
                template_name="document_rejected",
                recipient_email=association.user.email,
                context={
                    "association_name": association.name,
                    "rejection_reason": rejection_reason or "Aucune raison fournie",
                },
            )
        except Exception as e:
            # Log error but don't fail the operation
            logging.error(f"Failed to send document rejection email: {e}")

    return db_document


def delete_document(session: Session, document_id: int) -> None:
    """
    Delete a document and its associated file from storage.

    Parameters:
        session: Database session.
        document_id: Primary key of the document to delete.

    Raises:
        NotFoundError: If no document exists with the given ID.
    """
    db_document = get_document(session, document_id)
    if not db_document:
        raise NotFoundError("Document", document_id)

    # Delete file from storage if it exists
    try:
        storage_service.delete_file(db_document.url_doc)
    except Exception:
        # Continue with DB deletion even if file deletion fails
        # File might already be deleted or storage might be unavailable
        pass

    session.delete(db_document)
    session.flush()


def verify_document_ownership(document: Document, association_id: int) -> None:
    """
    Verify that a document belongs to the specified association.

    Parameters:
        document: The document to check.
        association_id: The association claiming ownership.

    Raises:
        InsufficientPermissionsError: If the document doesn't belong to the association.
    """
    if document.id_asso != association_id:
        raise InsufficientPermissionsError("access this document")


def can_association_create_missions(session: Session, association_id: int) -> bool:
    """
    Check if an association is allowed to create missions.

    An association can create missions only if their verification status is APPROVED.

    Parameters:
        session: Database session.
        association_id: The association to check.

    Returns:
        bool: True if association can create missions, False otherwise.
    """
    association = association_service.get_association(session, association_id)
    if not association:
        return False

    return association.verification_status == ProcessingStatus.APPROVED
