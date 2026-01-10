"""Document router module for association document management."""

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import DocumentCreate, DocumentPublic
from app.services import document as document_service
from app.services import association as association_service
from app.services.storage import storage_service
from app.exceptions import NotFoundError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[
        UploadFile, File(description="Document file to upload (PDF, image, etc.)")
    ],
    doc_name: Annotated[str, Form(description="Display name for the document")],
) -> DocumentPublic:
    """
    Upload a validation document for the authenticated association.

    This endpoint allows associations to upload documents (RNA certificates, registration
    papers, etc.) for admin validation. The document will be stored in MinIO and a database
    record created with PENDING status.

    ### Authentication Required:
    - Must be an authenticated association user
    - File is uploaded to MinIO object storage
    - Document status is initially set to PENDING

    ### File Requirements:
    - Maximum file size enforced by storage service
    - Recommended formats: PDF, JPG, PNG
    - File is stored with a unique name to prevent conflicts

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).
        `file`: The document file to upload (multipart/form-data).
        `doc_name`: Human-readable name for the document.

    Returns:
        `DocumentPublic`: The created document record with PENDING verification status.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the authenticated user has no association profile.
        `400 Bad Request`: If file upload fails or file is too large.
    """
    # Verify user has an association profile
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    assert association.id_asso is not None

    # Read file content
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename",
        )

    file_content = await file.read()

    # Upload file to storage
    try:
        # Convert bytes to BinaryIO (BytesIO)
        from io import BytesIO

        file_data = BytesIO(file_content)

        object_name = storage_service.upload_file(
            file_data=file_data,
            file_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=str(current_user.id_user) if current_user.id_user else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload failed: {str(e)}",
        )

    # Create document record
    document_in = DocumentCreate(
        doc_name=doc_name,
        url_doc=object_name,  # Store the object name/key
        id_asso=association.id_asso,
    )

    db_document = document_service.create_document(
        session, document_in, association.id_asso
    )

    return DocumentPublic.model_validate(db_document)


@router.get("/me", response_model=list[DocumentPublic])
def read_my_documents(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentPublic]:
    """
    Retrieve all documents uploaded by the authenticated association.

    Returns a list of all documents (pending, approved, rejected) for the current
    association, ordered by upload date (most recent first).

    ### Authentication Required:
    This endpoint requires a valid authentication token for an association user.

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `list[DocumentPublic]`: List of all documents for the association, including
            verification status and rejection reasons (if any).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the authenticated user has no association profile.
    """
    # Verify user has an association profile
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    assert association.id_asso is not None
    documents = document_service.get_documents_by_association(
        session, association.id_asso
    )

    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentPublic)
def read_document(
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
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
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `DocumentPublic`: The document's complete information including verification
            status and rejection reason (if applicable).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Verify user has an association profile
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    assert association.id_asso is not None
    document_service.verify_document_ownership(document, association.id_asso)

    return DocumentPublic.model_validate(document)


@router.get("/{document_id}/download-url")
def get_document_download_url(
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
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
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `dict`: Object containing:
            - `download_url`: Temporary presigned URL for downloading the file (str or None)
            - `expires_in`: Time in seconds until the URL expires (int)

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Verify user has an association profile
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    assert association.id_asso is not None
    document_service.verify_document_ownership(document, association.id_asso)

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
    current_user: Annotated[User, Depends(get_current_user)],
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
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If document or association profile doesn't exist.
        `403 InsufficientPermissionsError`: If document belongs to another association.
    """
    # Verify user has an association profile
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Verify ownership
    assert association.id_asso is not None
    document_service.verify_document_ownership(document, association.id_asso)

    # Delete document
    document_service.delete_document(session, document_id)
