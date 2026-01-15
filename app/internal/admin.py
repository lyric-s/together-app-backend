from typing import Annotated

from fastapi import APIRouter, Depends, Body, Query
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_admin

from app.models.admin import Admin, AdminCreate, AdminPublic
from app.models.document import DocumentPublic
from app.models.association import AssociationPublic
from app.models.report import ReportPublic, ReportUpdate
from app.models.category import CategoryPublic, CategoryCreate, CategoryUpdate
from app.models.location import (
    LocationPublic,
    LocationCreate,
    LocationUpdate,
    LocationWithCount,
)
from app.services import admin as admin_service
from app.services import document as document_service
from app.services import association as association_service
from app.services import volunteer as volunteer_service
from app.services import mission as mission_service
from app.services import report as report_service
from app.services import category as category_service
from app.services import location as location_service
from app.exceptions import NotFoundError, AuthenticationError, ValidationError

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
    admin = admin_service.create_admin(session, admin_in)
    session.commit()
    session.refresh(admin)
    return admin


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
async def approve_document(
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
    5. Email notification is sent to the association

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
        `401 Unauthorized`: If no valid admin authentication token is provided or admin ID is missing.
        `404 NotFoundError`: If document doesn't exist.
        `422 ValidationError`: If document is not in PENDING status.
    """
    if current_admin.id_admin is None:
        raise AuthenticationError("Admin ID is unexpectedly missing")

    approved_document = await document_service.approve_document(
        session, document_id, current_admin.id_admin
    )
    session.commit()
    session.refresh(approved_document)
    return DocumentPublic.model_validate(approved_document)


@router.post("/documents/{document_id}/reject", response_model=DocumentPublic)
async def reject_document(
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
    6. Email notification is sent to the association

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
        `401 Unauthorized`: If no valid admin authentication token is provided or admin ID is missing.
        `404 NotFoundError`: If document doesn't exist.
        `422 ValidationError`: If document is not in PENDING status.
    """
    if current_admin.id_admin is None:
        raise AuthenticationError("Admin ID is unexpectedly missing")

    rejected_document = await document_service.reject_document(
        session, document_id, current_admin.id_admin, rejection_reason
    )
    session.commit()
    session.refresh(rejected_document)
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
    session.commit()


@router.get("/documents/{document_id}/download-url")
def get_document_download_url(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> dict[str, str | int]:
    """
    Generate a temporary download URL for a document.

    Creates a presigned URL that **triggers a file download** when accessed.
    The URL expires after 1 hour. Admins can generate download URLs for any
    document regardless of ownership or status.

    **Behavior**: When the frontend opens this URL, the browser will **download**
    the file (save to disk) instead of displaying it inline.

    **Use this endpoint when**: You want users to save/download the document to their device.

    **For browser preview/viewing**, use `/documents/{document_id}/preview-url` instead.

    ## Use Cases

    - **Download for Offline Review**: Download documents to review offline
    - **Save Documents**: Allow admins to save documents locally
    - **Attachment Downloads**: Trigger file download in browser

    ## Authorization Required

    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ## URL Expiration

    The generated URL expires after **1 hour (3600 seconds)**. After expiration,
    a new URL must be requested.

    ## Example Response

    ```json
    {
      "download_url": "http://your-minio-endpoint:9000/together-uploads/1/abc_certificate.pdf?X-Amz-Algorithm=...",
      "expires_in": 3600
    }
    ```

    **Note**: The actual URL domain depends on your `MINIO_ENDPOINT` configuration.

    ## Frontend Usage Example

    ```javascript
    // Trigger download in browser
    const response = await fetch('/admin/documents/123/download-url');
    const { download_url } = await response.json();

    // Open URL to trigger download
    window.open(download_url, '_blank');
    // or
    window.location.href = download_url;
    ```

    Args:
        `document_id`: The unique identifier of the document.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `dict`: Object containing:
            - `download_url`: Temporary presigned URL that triggers file download
            - `expires_in`: Time in seconds until the URL expires (3600 = 1 hour)

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
    """
    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Generate presigned URL for download (inline=False, default)
    from app.services.storage import storage_service

    download_url = storage_service.get_presigned_url(document.url_doc, inline=False)
    if not download_url:
        raise ValidationError(
            f"Failed to generate download URL for document {document_id}. "
            "The storage service may be unavailable or the document file may not exist.",
            field="url_doc",
        )

    return {
        "download_url": download_url,
        "expires_in": 3600,  # 1 hour expiry
    }


@router.get("/documents/{document_id}/preview-url")
def get_document_preview_url(
    *,
    document_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> dict[str, str | int]:
    """
    Generate a temporary preview URL for a document.

    Creates a presigned URL that **displays the document in the browser** when accessed.
    The URL expires after 1 hour. Admins can generate preview URLs for any document
    regardless of ownership or status.

    **Behavior**: When the frontend opens this URL, the browser will **display**
    the document inline (PDF viewer, image display) instead of downloading it.

    **Use this endpoint when**: You want to preview/view documents directly in the browser.

    **For file download**, use `/documents/{document_id}/download-url` instead.

    ## Supported File Types

    - **PDF files** (`.pdf`): Display in browser's built-in PDF viewer
    - **Images** (`.jpg`, `.png`, `.gif`): Display inline as images
    - **Other formats**: Browser behavior varies (may still trigger download)

    ## Use Cases

    - **Document Verification**: Quick preview during admin review process
    - **PDF Viewer**: Display documents in browser without downloading
    - **Image Preview**: Show uploaded images inline
    - **Iframe Embedding**: Embed document preview in admin dashboard

    ## Authorization Required

    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ## URL Expiration

    The generated URL expires after **1 hour (3600 seconds)**. After expiration,
    a new URL must be requested.

    ## Example Response

    ```json
    {
      "preview_url": "http://your-minio-endpoint:9000/together-uploads/1/abc_cert.pdf?response-content-disposition=inline&X-Amz-Algorithm=...",
      "expires_in": 3600
    }
    ```

    **Note**: The actual URL domain depends on your `MINIO_ENDPOINT` configuration.

    ## Frontend Usage Examples

    ### Option 1: Open in New Tab

    ```javascript
    const response = await fetch('/admin/documents/123/preview-url');
    const { preview_url } = await response.json();

    // Open document in new browser tab for preview
    window.open(preview_url, '_blank');
    ```

    ### Option 2: Embed in Iframe

    ```javascript
    const response = await fetch('/admin/documents/123/preview-url');
    const { preview_url } = await response.json();

    // Display in iframe for in-dashboard preview
    document.getElementById('doc-preview').src = preview_url;
    ```

    ```html
    <iframe id="doc-preview" width="100%" height="600px"></iframe>
    ```

    ### Option 3: Direct Image Display

    ```javascript
    const response = await fetch('/admin/documents/123/preview-url');
    const { preview_url } = await response.json();

    // Display image inline
    document.getElementById('doc-image').src = preview_url;
    ```

    ```html
    <img id="doc-image" alt="Document preview" />
    ```

    Args:
        `document_id`: The unique identifier of the document.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `dict`: Object containing:
            - `preview_url`: Temporary presigned URL for inline browser display
            - `expires_in`: Time in seconds until the URL expires (3600 = 1 hour)

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If document doesn't exist.
    """
    # Get document
    document = document_service.get_document(session, document_id)
    if not document:
        raise NotFoundError("Document", document_id)

    # Generate presigned URL for inline preview (inline=True)
    from app.services.storage import storage_service

    preview_url = storage_service.get_presigned_url(document.url_doc, inline=True)
    if not preview_url:
        raise ValidationError(
            f"Failed to generate preview URL for document {document_id}. "
            "The storage service may be unavailable or the document file may not exist.",
            field="url_doc",
        )

    return {
        "preview_url": preview_url,
        "expires_in": 3600,  # 1 hour expiry
    }


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
async def delete_association(
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

    Sends email notification to the user before deletion.

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
    await association_service.delete_association(session, association_id)
    session.commit()


@router.get(
    "/associations/{association_id}/documents/latest", response_model=DocumentPublic
)
def get_latest_association_document(
    *,
    association_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> DocumentPublic:
    """
    Retrieve the latest document for a specific association.

    Returns the most recently uploaded document for the specified association,
    regardless of its verification status.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        `association_id`: The unique identifier of the association.
        `session`: Database session (automatically injected).
        `current_admin`: Authenticated admin (automatically injected from token).

    Returns:
        `DocumentPublic`: The latest document's complete information.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `404 NotFoundError`: If no documents exist for this association.
    """
    document = document_service.get_latest_document_by_association(
        session, association_id
    )
    if not document:
        raise NotFoundError("Document for association", association_id)

    return DocumentPublic.model_validate(document)


# Volunteer management endpoints


@router.delete("/volunteers/{volunteer_id}", status_code=204)
async def delete_volunteer(
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

    Sends email notification to the user before deletion.

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
    await volunteer_service.delete_volunteer(session, volunteer_id)
    session.commit()


# Mission management endpoints


@router.delete("/missions/{mission_id}", status_code=204)
async def delete_mission(
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

    Sends email notifications to:
    - The association that created the mission
    - All volunteers with approved applications

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
    await mission_service.delete_mission(session, mission_id, association_id=None)
    session.commit()


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
    return [
        ReportPublic.model_validate(report_service.to_report_public(r)) for r in reports
    ]


@router.patch("/reports/{report_id}", response_model=ReportPublic)
def update_report_state(
    *,
    report_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    report_update: ReportUpdate,
) -> ReportPublic:
    """
    Update report processing state (approve/reject).

    Allows admins to change the state of a report to approve or reject it.
    When updating, the report is reloaded with relationships to compute display names.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### State Transitions:
    - PENDING → APPROVED: Accept the report as valid
    - PENDING → REJECTED: Dismiss the report as invalid
    - Can also transition between APPROVED and REJECTED

    Args:
        report_id: The unique identifier of the report to update.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        report_update: Update data containing the new state.

    Returns:
        ReportPublic: The updated report with reporter and reported user names.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If report doesn't exist.
    """
    from app.models.report import Report
    from sqlmodel import select
    from sqlalchemy.orm import selectinload
    from app.models.user import User

    # Update the report
    report_service.update_report(session, report_id, report_update)
    session.commit()

    # Reload with relationships for name resolution
    report_with_relations = session.exec(
        select(Report)
        .where(Report.id_report == report_id)
        .options(
            selectinload(Report.reporter).selectinload(User.volunteer_profile),  # type: ignore
            selectinload(Report.reporter).selectinload(User.association_profile),  # type: ignore
            selectinload(Report.reported_user).selectinload(User.volunteer_profile),  # type: ignore
            selectinload(Report.reported_user).selectinload(User.association_profile),  # type: ignore
        )
    ).first()

    if not report_with_relations:
        raise NotFoundError("Report", report_id)

    return ReportPublic.model_validate(
        report_service.to_report_public(report_with_relations)
    )


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


# Category management endpoints


@router.get("/categories", response_model=list[CategoryPublic])
def get_all_categories(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> list[CategoryPublic]:
    """
    Retrieve all categories.

    Returns complete list of all mission categories, ordered alphabetically.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        list[CategoryPublic]: All categories sorted alphabetically.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    categories = category_service.get_all_categories(session)
    return [CategoryPublic.model_validate(c) for c in categories]


@router.post("/categories", response_model=CategoryPublic, status_code=201)
def create_category(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    category_in: CategoryCreate,
) -> CategoryPublic:
    """
    Create a new category.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Validation:
    - Category label must be unique

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        category_in: Category data with label.

    Returns:
        CategoryPublic: The created category.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        400 AlreadyExistsError: If a category with the same label already exists.
    """
    category = category_service.create_category(session, category_in)
    session.commit()
    session.refresh(category)
    return CategoryPublic.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryPublic)
def update_category(
    *,
    category_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    category_update: CategoryUpdate,
) -> CategoryPublic:
    """
    Update a category.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Validation:
    - New label must be unique (if changing label)

    Args:
        category_id: The unique identifier of the category to update.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        category_update: Update data (label).

    Returns:
        CategoryPublic: The updated category.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If category doesn't exist.
        400 AlreadyExistsError: If new label conflicts with existing category.
    """
    category = category_service.update_category(session, category_id, category_update)
    session.commit()
    session.refresh(category)
    return CategoryPublic.model_validate(category)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    *,
    category_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete a category.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Warning:
    - This will fail if any missions are currently using this category
    - Remove category from all missions before attempting deletion

    Args:
        category_id: The unique identifier of the category to delete.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        None: Returns 204 No Content on successful deletion.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If category doesn't exist.
        400 IntegrityError: If missions are still using this category.
    """
    category_service.delete_category(session, category_id)
    session.commit()


# Analytics endpoints


@router.get("/stats/overview")
def get_overview_statistics(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
):
    """
    Get dashboard overview statistics.

    Returns key metrics for the admin dashboard including counts of validated
    associations, completed missions, total users, pending reports, and pending
    associations.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        OverviewStats: Overview statistics object.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    from app.services import analytics as analytics_service
    from app.models.analytics import OverviewStats

    stats = analytics_service.get_overview_statistics(session)
    return OverviewStats.model_validate(stats)


@router.get("/stats/volunteers-by-month")
def get_volunteers_by_month(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    months: int = Query(12, ge=1, le=24, description="Number of months (1-24)"),
):
    """
    Get volunteer registration counts by month.

    Returns monthly volunteer registration data for the specified number of months,
    useful for visualizing growth trends in chart format.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Query Parameters:
    - **months**: Number of months to include (default: 12, max: 24)

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        months: Number of months to retrieve (1-24, default: 12).

    Returns:
        list[MonthlyDataPoint]: List of monthly data points with format {"month": "YYYY-MM", "value": count}.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    from app.services import analytics as analytics_service
    from app.models.analytics import MonthlyDataPoint

    data = analytics_service.get_volunteers_by_month(session, months)
    return [MonthlyDataPoint.model_validate(d) for d in data]


@router.get("/stats/missions-by-month")
def get_missions_by_month(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    months: int = Query(12, ge=1, le=24, description="Number of months (1-24)"),
):
    """
    Get completed mission counts by month.

    Returns monthly completed mission data for the specified number of months,
    useful for tracking platform activity over time.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Query Parameters:
    - **months**: Number of months to include (default: 12, max: 24)

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        months: Number of months to retrieve (1-24, default: 12).

    Returns:
        list[MonthlyDataPoint]: List of monthly data points with format {"month": "YYYY-MM", "value": count}.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    from app.services import analytics as analytics_service
    from app.models.analytics import MonthlyDataPoint

    data = analytics_service.get_missions_by_month(session, months)
    return [MonthlyDataPoint.model_validate(d) for d in data]


@router.get("/reports/stats")
def get_report_statistics(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
):
    """
    Get report counts by processing state.

    Returns the total counts of reports grouped by their processing state
    (pending, accepted, rejected), useful for monitoring moderation workload.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        ReportStats: Report statistics with counts by state.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    from app.services import analytics as analytics_service
    from app.models.analytics import ReportStats

    stats = analytics_service.get_report_statistics(session)
    return ReportStats.model_validate(stats)


# Location management endpoints


@router.get("/locations", response_model=list[LocationWithCount])
def get_all_locations(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    offset: int = 0,
    limit: int = 100,
) -> list[LocationWithCount]:
    """
    Retrieve all locations with mission counts.

    Returns a paginated list of all locations in the system along with the count
    of missions associated with each location. Useful for managing locations and
    identifying unused ones.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Query Parameters:
    - **offset**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        offset: Pagination offset.
        limit: Maximum results per page.

    Returns:
        list[LocationWithCount]: List of locations with mission_count field.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
    """
    locations = location_service.get_all_locations_with_counts(
        session, offset=offset, limit=limit
    )
    return [LocationWithCount.model_validate(loc) for loc in locations]


@router.post("/locations", response_model=LocationPublic, status_code=201)
def create_location(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    location_in: LocationCreate,
) -> LocationPublic:
    """
    Create a new location.

    Creates a new location that can be used by missions. All fields are optional,
    allowing flexibility in how much location information is provided.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Request Body:
    - **address**: Street address (optional, max 255 chars)
    - **country**: Country name (optional, max 50 chars)
    - **zip_code**: Postal/ZIP code (optional, max 50 chars)
    - **lat**: Latitude coordinate (optional, -90 to 90)
    - **long**: Longitude coordinate (optional, -180 to 180)

    Args:
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        location_in: Location creation data.

    Returns:
        LocationPublic: The created location with generated ID.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        422 Validation Error: If location data is invalid.
    """
    location = location_service.create_location(session, location_in)
    session.commit()
    session.refresh(location)
    return LocationPublic.model_validate(location)


@router.get("/locations/{location_id}", response_model=LocationWithCount)
def get_location_by_id(
    *,
    location_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> LocationWithCount:
    """
    Retrieve a specific location by ID with mission count.

    Returns detailed information about a location including how many missions
    are currently using it.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    Args:
        location_id: The unique identifier of the location.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        LocationWithCount: The location with mission_count field.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If location doesn't exist.
    """
    location = location_service.get_location_with_mission_count(session, location_id)
    return LocationWithCount.model_validate(location)


@router.patch("/locations/{location_id}", response_model=LocationPublic)
def update_location(
    *,
    location_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
    location_update: LocationUpdate,
) -> LocationPublic:
    """
    Update an existing location.

    Updates location information. Only provided fields will be updated (partial update).
    Missions using this location will automatically reflect the updated information.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Request Body (all fields optional):
    - **address**: New street address (max 255 chars)
    - **country**: New country name (max 50 chars)
    - **zip_code**: New postal/ZIP code (max 50 chars)
    - **lat**: New latitude coordinate (-90 to 90)
    - **long**: New longitude coordinate (-180 to 180)

    Args:
        location_id: The unique identifier of the location to update.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).
        location_update: Update data (only provided fields will be updated).

    Returns:
        LocationPublic: The updated location.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If location doesn't exist.
        422 Validation Error: If update data is invalid.
    """
    location = location_service.update_location(session, location_id, location_update)
    session.commit()
    session.refresh(location)
    return LocationPublic.model_validate(location)


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(
    *,
    location_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[Admin, Depends(get_current_admin)],
) -> None:
    """
    Delete a location.

    Deletes a location from the system. The location can only be deleted if no
    missions are currently using it. If missions reference this location, they
    must be reassigned or deleted first.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Important:
    This operation will fail if any missions still reference this location.
    The error message will indicate how many missions are using it.

    Args:
        location_id: The unique identifier of the location to delete.
        session: Database session (automatically injected).
        current_admin: Authenticated admin (automatically injected from token).

    Returns:
        None: 204 No Content on success.

    Raises:
        401 Unauthorized: If no valid admin authentication token is provided.
        404 NotFoundError: If location doesn't exist.
        400 ValidationError: If location is still referenced by missions.
    """
    location_service.delete_location(session, location_id)
    session.commit()
