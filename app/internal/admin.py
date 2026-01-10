from typing import Annotated

from fastapi import APIRouter, Depends, Body
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_admin

from app.models.admin import Admin, AdminCreate, AdminPublic
from app.models.document import DocumentPublic
from app.models.association import AssociationPublic
from app.models.report import ReportPublic
from app.services import admin as admin_service
from app.services import document as document_service
from app.services import association as association_service
from app.services import volunteer as volunteer_service
from app.services import mission as mission_service
from app.services import report as report_service
from app.exceptions import NotFoundError

router = APIRouter(prefix="/internal/admin", tags=["admin"])


@router.post("/", response_model=AdminPublic, dependencies=[Depends(get_current_admin)])
def create_new_admin(
    *,
    session: Session = Depends(get_session),
    admin_in: AdminCreate,
):
    """
    Create a new admin account.

    Creates a new administrator account with the provided credentials. This endpoint
    requires admin authentication and can only be accessed by existing administrators.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Security:
    - Password is provided in plaintext and will be hashed before storage
    - Username and email must be unique
    - Created admin has full administrative privileges

    Args:
        `session`: Database session (automatically injected).
        `admin_in`: Data for the new admin including username, email, and plaintext password.

    Returns:
        `AdminPublic`: The created admin record with sensitive fields (password hash) removed.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `400 Bad Request`: If the username or email already exists.
    """
    return admin_service.create_admin(session, admin_in)


# Document validation endpoints


@router.get("/documents/pending", response_model=list[DocumentPublic])
def get_pending_documents(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> list[DocumentPublic]:
    """
    Retrieve all documents pending validation.

    Returns a list of all documents with PENDING verification status, ordered by
    upload date (oldest first - FIFO). This allows admins to see which documents
    need review.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `list[DocumentPublic]`: List of pending documents with association information.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
    """
    documents = document_service.get_pending_documents(session)
    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=DocumentPublic)
def get_document(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> DocumentPublic:
    """
    Retrieve a specific document by ID.

    Allows admins to view any document regardless of verification status or ownership.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        `document_id`: The unique identifier of the document to retrieve.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `DocumentPublic`: The document's complete information.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
    """
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    return DocumentPublic.model_validate(document)


@router.post("/documents/{document_id}/approve", response_model=DocumentPublic)
def approve_document(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> DocumentPublic:
    """
    Approve a pending document and enable the association to create missions.

    When a document is approved:
    1. Document verification status is set to APPROVED
    2. Admin ID is recorded on the document
    3. Association's verification_status is set to APPROVED
    4. Association can now create missions

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Validation:
    - Document must be in PENDING status
    - Cannot approve already approved or rejected documents

    Args:
        `document_id`: The unique identifier of the document to approve.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `DocumentPublic`: The approved document with updated status.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
        `422 ValidationError`: If document is not in PENDING status.
    """
    assert current_admin.id_admin is not None
    approved_document = document_service.approve_document(
        session, document_id, current_admin.id_admin
    )
    return DocumentPublic.model_validate(approved_document)


@router.post("/documents/{document_id}/reject", response_model=DocumentPublic)
def reject_document(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    rejection_reason: Annotated[
        str | None,
        Body(
            embed=True,
            description="Optional reason for rejection to help the association understand why",
        ),
    ] = None,
) -> DocumentPublic:
    """
    Reject a pending document and prevent the association from creating missions.

    When a document is rejected:
    1. Document verification status is set to REJECTED
    2. Admin ID is recorded on the document
    3. Rejection reason is stored (if provided)
    4. Association's verification_status is set to REJECTED
    5. Association cannot create missions until a new document is approved

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Validation:
    - Document must be in PENDING status
    - Cannot reject already approved or rejected documents

    ### Best Practices:
    - Always provide a rejection reason to help associations understand what's wrong
    - Be specific about what needs to be corrected

    Args:
        `document_id`: The unique identifier of the document to reject.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).
        `rejection_reason`: Optional explanation for why the document was rejected.

    Returns:
        `DocumentPublic`: The rejected document with updated status and reason.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
        `422 ValidationError`: If document is not in PENDING status.
    """
    assert current_admin.id_admin is not None
    rejected_document = document_service.reject_document(
        session, document_id, current_admin.id_admin, rejection_reason
    )
    return DocumentPublic.model_validate(rejected_document)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete a document and its file from storage.

    Permanently removes a document and its associated file. Admins can delete
    any document regardless of status or ownership.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Warning:
    This action is irreversible. Both the database record and the file in storage
    will be permanently deleted.

    Args:
        `document_id`: The unique identifier of the document to delete.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
    """
    document_service.delete_document(session, document_id)


# Association management endpoints


@router.get("/associations", response_model=list[AssociationPublic])
def get_all_associations(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> list[AssociationPublic]:
    """
    Retrieve all associations with their verification status.

    Returns a complete list of all registered associations, including their
    verification status, mission counts, and user information.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `list[AssociationPublic]`: List of all associations with verification status.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
    """
    # Get all associations (no limit)
    return association_service.get_associations(session, offset=0, limit=10000)


@router.delete("/associations/{association_id}", status_code=204)
def delete_association(
    *,
    association_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete an association and all related data.

    Permanently removes an association, including:
    - The association profile
    - The associated user account
    - All missions created by the association
    - All documents uploaded by the association
    - Related engagement and other data

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Warning:
    This action is irreversible and cascades to all related data.

    Args:
        `association_id`: The unique identifier of the association to delete.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If association doesn't exist.
    """
    association_service.delete_association(session, association_id)


# Volunteer management endpoints


@router.delete("/volunteers/{volunteer_id}", status_code=204)
def delete_volunteer(
    *,
    volunteer_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete a volunteer and all related data.

    Permanently removes a volunteer, including:
    - The volunteer profile
    - The associated user account
    - All engagements (mission applications)
    - All favorites
    - Related data

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Warning:
    This action is irreversible and cascades to all related data.

    Args:
        `volunteer_id`: The unique identifier of the volunteer to delete.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If volunteer doesn't exist.
    """
    volunteer_service.delete_volunteer(session, volunteer_id)


# Mission management endpoints


@router.delete("/missions/{mission_id}", status_code=204)
def delete_mission(
    *,
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete a mission and all related data.

    Permanently removes a mission, including:
    - The mission record
    - All engagements (volunteer applications)
    - All favorites referencing this mission
    - Related data

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Warning:
    This action is irreversible and cascades to all related data.

    Args:
        `mission_id`: The unique identifier of the mission to delete.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If mission doesn't exist.
    """
    # Admin can delete any mission without association_id check
    mission_service.delete_mission(session, mission_id, association_id=None)


# Report management endpoints


@router.get("/reports", response_model=list[ReportPublic])
def get_all_reports(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    offset: int = 0,
    limit: int = 100,
) -> list[ReportPublic]:
    """
    Retrieve all user reports.

    Returns a paginated list of all reports submitted by users, ordered by
    most recent first. Allows admins to monitor and moderate user behavior.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).
        `offset`: Number of records to skip (default: 0).
        `limit`: Maximum number of records to return (default: 100).

    Returns:
        `list[ReportPublic]`: List of all reports ordered by date (newest first).

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
    """
    reports = report_service.get_all_reports(session, offset=offset, limit=limit)
    return [ReportPublic.model_validate(r) for r in reports]


# Document list endpoint


@router.get("/documents", response_model=list[DocumentPublic])
def get_all_documents_list(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    offset: int = 0,
    limit: int = 100,
) -> list[DocumentPublic]:
    """
    Retrieve all documents regardless of status.

    Returns a paginated list of all documents (pending, approved, rejected),
    ordered by most recent first. Provides a comprehensive view of all
    validation documents in the system.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Note:
    For pending documents specifically, use `/documents/pending` instead.

    Args:
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).
        `offset`: Number of records to skip (default: 0).
        `limit`: Maximum number of records to return (default: 100).

    Returns:
        `list[DocumentPublic]`: List of all documents ordered by date (newest first).

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
    """
    documents = document_service.get_all_documents(session, offset=offset, limit=limit)
    return [DocumentPublic.model_validate(doc) for doc in documents]
