"""Document router module for association document management."""

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_association
from app.models.association import Association
from app.models.document import DocumentCreate, DocumentPublic
from app.services import document as document_service
from app.services.storage import storage_service
from app.exceptions import NotFoundError, ValidationError
from app.utils.validation import ensure_id
from app.utils.logger import logger

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
    file: Annotated[
        UploadFile, File(description="Document file to upload (PDF, image, etc.)")
    ],
    doc_name: Annotated[str, Form(description="Display name for the document")],
) -> DocumentPublic:
    """
    Upload a validation document for the authenticated association.

    This endpoint allows associations to upload documents (RNA certificates, registration
    papers, etc.) for admin validation. The document will be stored in MinIO and a database
    record created with `PENDING` status awaiting admin approval.

    ## Request Format

    This endpoint uses `multipart/form-data` encoding:

    - `file` (file, required): Document file to upload (PDF, JPG, PNG)
    - `doc_name` (string, required): Display name for the document

    ## Example Request

    ```http
    POST /documents/upload HTTP/1.1
    Authorization: Bearer your_jwt_token
    Content-Type: multipart/form-data; boundary=----FormBoundary

    ------FormBoundary
    Content-Disposition: form-data; name="file"; filename="rna_certificate.pdf"
    Content-Type: application/pdf

    [Binary PDF data]
    ------FormBoundary
    Content-Disposition: form-data; name="doc_name"

    RNA Registration Certificate 2025
    ------FormBoundary--
    ```

    ## Example Response (201 Created)

    ```json
    {
      "id_doc": 123,
      "doc_name": "RNA Registration Certificate 2025",
      "url_doc": "documents/user_42/rna_certificate_1704531600.pdf",
      "id_asso": 5,
      "verif_state": "PENDING",
      "rejection_reason": null,
      "date_uploaded": "2026-01-14T10:30:00Z"
    }
    ```

    ## File Requirements

    - **Maximum file size**: Enforced by storage service (typically 10MB)
    - **Recommended formats**: PDF, JPG, PNG
    - **Storage**: Files are stored in MinIO object storage with unique names
    - **Initial status**: All uploaded documents start with `PENDING` verification status

    ## Document Lifecycle

    1. **Upload** (this endpoint) → Status: `PENDING`
    2. **Admin Review** → Status changed to `APPROVED` or `REJECTED`
    3. **If Rejected** → Association can upload a new document

    Parameters:
        session: Database session (automatically injected via `Depends(get_session)`).
        current_association: Authenticated association profile (automatically injected via `Depends(get_current_association)`).
        file: The document file to upload (multipart/form-data).
        doc_name: Human-readable name for the document.

    Returns:
        `DocumentPublic`: The created document record with `PENDING` verification status.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the authenticated user has no association profile.
        `400 ValidationError`: If file upload fails, file is too large, or filename is missing.
    """
    # Read file content
    if not file.filename:
        raise ValidationError("File must have a filename")

    # Upload file to storage
    try:
        file.file.seek(0)
        object_name = storage_service.upload_file(
            file_data=file.file,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=str(ensure_id(current_association.id_user, "User")),
        )
    except Exception as e:
        logger.exception(e)
        raise ValidationError("File upload failed")

    # Create document record
    association_id = ensure_id(current_association.id_asso, "Association")
    document_in = DocumentCreate(
        doc_name=doc_name,
        url_doc=object_name,  # Store the object name/key
        id_asso=association_id,
    )

    db_document = document_service.create_document(
        session,
        association_id,
        document_in,
    )
    session.commit()
    session.refresh(db_document)

    return DocumentPublic.model_validate(db_document)


@router.get("/me", response_model=list[DocumentPublic])
def read_my_documents(
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> list[DocumentPublic]:
    """
    Retrieve all documents uploaded by the authenticated association.

    Returns a list of all documents (pending, approved, rejected) for the current
    association, ordered by upload date (most recent first). Use this endpoint to
    display a document management dashboard.

    ## Example Request

    ```
    GET /documents/me
    Authorization: Bearer your_jwt_token
    ```

    ## Example Response

    ```json
    [
      {
        "id_doc": 123,
        "doc_name": "RNA Registration Certificate 2025",
        "url_doc": "documents/user_42/rna_certificate_1704531600.pdf",
        "id_asso": 5,
        "verif_state": "APPROVED",
        "rejection_reason": null,
        "date_uploaded": "2026-01-14T10:30:00Z"
      },
      {
        "id_doc": 122,
        "doc_name": "Tax Exemption Certificate",
        "url_doc": "documents/user_42/tax_cert_1704445200.pdf",
        "id_asso": 5,
        "verif_state": "REJECTED",
        "rejection_reason": "Document is expired. Please upload a current certificate dated within the last 12 months.",
        "date_uploaded": "2026-01-13T08:15:00Z"
      },
      {
        "id_doc": 121,
        "doc_name": "Insurance Certificate 2026",
        "url_doc": "documents/user_42/insurance_1704358800.pdf",
        "id_asso": 5,
        "verif_state": "PENDING",
        "rejection_reason": null,
        "date_uploaded": "2026-01-12T14:45:00Z"
      }
    ]
    ```

    ## Document Statuses

    - `PENDING`: Awaiting admin review
    - `APPROVED`: Document verified and accepted
    - `REJECTED`: Document rejected (see `rejection_reason` for details)

    Parameters:
        session: Database session (automatically injected via `Depends(get_session)`).
        current_association: Authenticated association profile (automatically injected via `Depends(get_current_association)`).

    Returns:
        `list[DocumentPublic]`: List of all documents for the association, ordered by upload date (most recent first).
            Each document includes verification status and rejection reason (if rejected).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the authenticated user has no association profile.
    """
    documents = document_service.get_documents_by_association(
        session,
        current_association.id_asso,  # type: ignore
    )

    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentPublic)
def read_document(
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> DocumentPublic:
    """
    Retrieve a specific document by ID.

    Returns detailed information about a document. Only the document owner
    (association) can access their documents.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Document must belong to the authenticated association

    Args:
        `document_id`: The unique identifier of the document to retrieve.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `DocumentPublic`: The document's complete information including verification
            status and rejection reason (if applicable).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    document_service.verify_document_ownership(
        document,
        current_association.id_asso,  # type: ignore
    )

    return DocumentPublic.model_validate(document)


@router.get("/{document_id}/download-url")
def get_document_download_url(
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> dict[str, str | int]:
    """
    Generate a temporary download URL for a document.

    Creates a presigned URL that allows temporary access to download the document
    file from storage. The URL expires after a configurable time period.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Document must belong to the authenticated association

    Args:
        `document_id`: The unique identifier of the document.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `dict`: Object containing:
            - `download_url`: Temporary presigned URL for downloading the file (str or None)
            - `expires_in`: Time in seconds until the URL expires (int)

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    document_service.verify_document_ownership(
        document,
        current_association.id_asso,  # type: ignore
    )

    # Generate presigned URL (returns None | str)
    download_url = storage_service.get_presigned_url(document.url_doc)

    return {
        "download_url": download_url or "",
        "expires_in": 3600,  # Default expiry from storage service (1 hour)
    }


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> None:
    """
    Delete a document and its file from storage.

    Permanently removes a document and its associated file. This action is only
    permitted for the association that uploaded the document.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Document must belong to the authenticated association

    ### Warning:
    This action is irreversible. Both the database record and the file in storage
    will be permanently deleted.

    Args:
        `document_id`: The unique identifier of the document to delete.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    document_service.verify_document_ownership(
        document,
        current_association.id_asso,  # type: ignore
    )

    # Delete document
    document_service.delete_document(session, document_id)
    session.commit()
