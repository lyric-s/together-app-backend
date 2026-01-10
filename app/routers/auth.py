from app.models.token import TokenRefreshRequest
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel import Session
import jwt
from jwt.exceptions import InvalidTokenError as PyJWTInvalidTokenError

from app.database.database import get_session
from app.core.config import get_settings, Settings
from app.core.security import (
    authenticate_user,
    authenticate_admin,
    create_access_token,
    create_refresh_token,
)
from app.core.password import get_token_hash, verify_token
from app.core.limiter import limiter
from app.models.token import Token
from app.models.user import User
from app.models.password_reset import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
)
from app.exceptions import InvalidCredentialsError, InvalidTokenError, NotFoundError
from app.services import user as user_service
from app.services.email import send_password_reset_email
from sqlmodel import select

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Authenticate user (or admin) credentials and issue access and refresh tokens.

    Authenticates user credentials from the OAuth2 form and issues a new access token
    and refresh token for authorized API access.

    ### Rate Limiting:
    - **Limit**: 5 attempts per minute per IP address.

    ### OAuth2 Password Flow:
    - Accepts `username` and `password` via form data
    - **Unified Login**: Attempts to authenticate as a standard user first. If not found, attempts to authenticate as an admin.
    - Returns access token, refresh token (for users), and `user_type` ("volunteer", "association", or "admin").

    Args:
        `request`: The incoming HTTP request (required for rate limiting).
        `form_data`: OAuth2 form data containing `username` and `password`.
        `session`: Database session (automatically injected).
        `settings`: Application settings (automatically injected).

    Returns:
        `Token`: Token object containing `access_token`, `refresh_token`, `token_type` ("bearer"), and `user_type`.

    Raises:
        `401 Unauthorized`: If the provided username or password is incorrect for both user and admin accounts.
        `429 Too Many Requests`: When the rate limit is exceeded.
    """
    # Try authenticating as a standard user first
    user = authenticate_user(session, form_data.username, form_data.password)

    if user:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.username}, expires_delta=refresh_token_expires
        )

        # Store hashed refresh token
        user.hashed_refresh_token = get_token_hash(refresh_token)
        session.add(user)
        session.commit()
        session.refresh(user)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user_type=user.user_type,
        )

    # If not a user, try authenticating as an admin
    admin = authenticate_admin(session, form_data.username, form_data.password)

    if admin:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # Admin tokens get the special "mode": "admin" claim
        access_token = create_access_token(
            data={"sub": admin.username, "mode": "admin"},
            expires_delta=access_token_expires,
        )
        # Admins typically don't use refresh tokens in this setup, or we can choose not to issue one
        # consistent with the separate admin login endpoint behavior

        return Token(
            access_token=access_token,
            refresh_token=None,
            token_type="bearer",
            user_type="admin",
        )

    # If neither user nor admin found
    raise InvalidCredentialsError()


@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    request_data: TokenRefreshRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Validate a refresh token and issue a new access token.

    Validates the provided refresh token, ensures it belongs to an existing user and is of
    type "refresh", then returns a Token containing a newly created access token and the
    original refresh token.

    ### Rate Limiting:
    - **Limit**: 5 attempts per minute per IP address.

    ### Token Refresh Flow:
    - Validates the refresh token signature and expiration
    - Verifies the token type is "refresh"
    - Confirms the user still exists in the database
    - Issues a new access token with updated expiration

    Args:
        `request`: The incoming HTTP request (required for rate limiting).
        `request_data`: Request body containing the `refresh_token` string.
        `session`: Database session (automatically injected).
        `settings`: Application settings (automatically injected).

    Returns:
        `Token`: Object with `access_token` (newly issued), `refresh_token` (the incoming token),
            and `token_type` set to "bearer".

    Raises:
        `401 Unauthorized`: If the refresh token is invalid, expired, missing required claims,
            or the user does not exist.
        `429 Too Many Requests`: When the rate limit is exceeded.
    """
    incoming_refresh_token = request_data.refresh_token

    try:
        payload = jwt.decode(
            incoming_refresh_token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if username is None or token_type != "refresh":
            raise InvalidTokenError("Invalid token claims")

        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise InvalidTokenError("User no longer exists")

        # Verify the refresh token matches the one stored in DB
        if not user.hashed_refresh_token or not verify_token(
            incoming_refresh_token, user.hashed_refresh_token
        ):
            raise InvalidTokenError("Token has been revoked or replaced")

    except PyJWTInvalidTokenError:
        raise InvalidTokenError()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    # Token Rotation: Issue a new refresh token and invalidate the old one
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        data={"sub": username}, expires_delta=refresh_token_expires
    )

    user.hashed_refresh_token = get_token_hash(new_refresh_token)
    session.add(user)
    session.commit()
    session.refresh(user)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_type=user.user_type,
    )


@router.post("/password-reset/request", response_model=PasswordResetResponse)
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Request a password reset email.

    Generates a password reset token and sends it via email to the user.
    Always returns success to prevent email enumeration attacks.

    ### Rate Limiting:
    - **Limit**: 3 attempts per hour per IP address.

    ### Security:
    - Email enumeration protection: Always returns success message
    - Tokens expire after 30 minutes (configurable)
    - Tokens are cryptographically random and stored as hashes

    Args:
        request: The incoming HTTP request (required for rate limiting).
        reset_request: Request body containing the user's email address.
        session: Database session (automatically injected).

    Returns:
        PasswordResetResponse: Success message (returned regardless of email existence).

    Raises:
        429 Too Many Requests: When the rate limit is exceeded.
    """
    try:
        user, reset_token = user_service.create_password_reset_token(
            session, reset_request.email
        )
        await send_password_reset_email(
            email=user.email,
            reset_token=reset_token,
            username=user.username,
        )
    except NotFoundError:
        # Don't reveal if email exists - timing-safe response
        pass
    except Exception:
        # Log but don't expose errors to prevent information leakage
        pass

    return PasswordResetResponse(
        message="If that email exists, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
@limiter.limit("5/hour")
async def confirm_password_reset(
    request: Request,
    reset_confirm: PasswordResetConfirm,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Confirm password reset with token.

    Validates the password reset token and updates the user's password.

    ### Rate Limiting:
    - **Limit**: 5 attempts per hour per IP address.

    ### Security:
    - Token is validated and must not be expired
    - Old refresh tokens are invalidated (forces re-login)
    - Token is single-use (cleared after successful reset)

    Args:
        request: The incoming HTTP request (required for rate limiting).
        reset_confirm: Request body containing the reset token and new password.
        session: Database session (automatically injected).

    Returns:
        PasswordResetResponse: Success message indicating password has been reset.

    Raises:
        401 Unauthorized: If the token is invalid or expired.
        429 Too Many Requests: When the rate limit is exceeded.
    """
    user_service.reset_password_with_token(
        session, reset_confirm.token, reset_confirm.new_password
    )
    return PasswordResetResponse(
        message="Password has been reset successfully. Please log in with your new password."
    )


@router.get("/me")
async def get_current_profile(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Get authenticated user or admin profile with complete information.

    This endpoint automatically detects the authentication context from the JWT token
    and returns the appropriate profile structure based on the user type.

    ### Authentication Required:
    - **Bearer token**: Valid JWT access token in Authorization header
    - **Token types supported**: User tokens (volunteer/association) and admin tokens

    ### Response Types:
    The response structure varies based on the authenticated entity type:

    **For Volunteers** (`user_type: "volunteer"`):
    - `user`: Complete user account information (UserPublic)
    - `profile`: Volunteer-specific data including mission counts (VolunteerPublic)

    **For Associations** (`user_type: "association"`):
    - `user`: Complete user account information (UserPublic)
    - `profile`: Association-specific data including mission counts (AssociationPublic)

    **For Admins** (`user_type: "admin"`):
    - `profile`: Admin account information (AdminPublic)
    - Note: Admins don't have a separate User entity

    ### How Token Detection Works:
    1. Decodes the JWT access token from the Authorization header
    2. Checks the `mode` claim to distinguish between admin and user tokens
    3. Loads the appropriate profile with all related data
    4. Returns the profile in the correct format for the frontend

    Args:
        token: JWT access token extracted from Authorization header (automatically injected)
        session: Database session (automatically injected)

    Returns:
        Union[VolunteerProfile, AssociationProfile, AdminProfile]: Profile data structure
        matching the authenticated user type

    Raises:
        `401 Unauthorized`: If token is invalid, expired, or profile doesn't exist

    Example:
        ```bash
        curl -H "Authorization: Bearer <token>" http://api/auth/me
        ```
    """
    from app.services import admin as admin_service
    from fastapi import HTTPException, status

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        mode: str | None = payload.get("mode")
        token_type: str | None = payload.get("type")

        if username is None or token_type != "access":
            raise credentials_exception

        # Check if it's an admin token
        if mode == "admin":
            admin = admin_service.get_admin_by_username(session, username)
            if not admin:
                raise credentials_exception
            return admin_service.get_admin_profile(admin)

        # Otherwise it's a user token
        user = user_service.get_user_by_username(session, username)
        if not user:
            raise credentials_exception
        return user_service.get_user_with_profile(session, user)

    except PyJWTInvalidTokenError:
        raise credentials_exception
