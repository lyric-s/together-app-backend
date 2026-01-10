"""Email service using Brevo SMTP."""

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import get_settings


def get_email_config() -> ConnectionConfig:
    """
    Create and return email configuration for FastMail.

    Returns:
        ConnectionConfig: Configuration object for email sending using Brevo SMTP.

    Raises:
        ValueError: If required email settings are not configured.
    """
    settings = get_settings()

    # Validate required settings
    if not settings.SMTP_USER:
        raise ValueError("SMTP_USER is required for email functionality")
    if not settings.SMTP_PASSWORD:
        raise ValueError("SMTP_PASSWORD is required for email functionality")
    if not settings.SMTP_FROM_EMAIL:
        raise ValueError("SMTP_FROM_EMAIL is required for email functionality")

    return ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASSWORD.get_secret_value(),
        MAIL_FROM=settings.SMTP_FROM_EMAIL,
        MAIL_FROM_NAME=settings.SMTP_FROM_NAME,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


async def send_password_reset_email(
    email: EmailStr, reset_token: str, username: str
) -> None:
    """
    Send password reset email to user.

    Args:
        email: User's email address
        reset_token: Password reset token (URL-safe)
        username: User's username for personalization

    Returns:
        None

    Raises:
        ValueError: If email settings are not configured.
        Exception: If email sending fails.
    """
    settings = get_settings()

    if not settings.FRONTEND_URL:
        raise ValueError("FRONTEND_URL is required for password reset functionality")

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html_body = f"""
    <html>
    <body>
      <h2>Password Reset Request</h2>
      <p>Hello {username},</p>
      <p>You requested to reset your password. Click the link below to proceed:</p>
      <p><a href="{reset_url}">Reset Password</a></p>
      <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
      <p>If you didn't request this password reset, please ignore this email.</p>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=html_body,
        subtype=MessageType.html,
    )

    fm = FastMail(get_email_config())
    await fm.send_message(message)
