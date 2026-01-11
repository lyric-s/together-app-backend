"""Email service using Brevo SMTP with notification templates."""

from typing import Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import get_settings


# Email template definitions
EMAIL_TEMPLATES = {
    "document_approved": {
        "subject": "Document approuvé - Together Platform",
        "body": """
            <html><body>
            <h2>Document Approuvé</h2>
            <p>Bonjour {association_name},</p>
            <p>Votre document a été approuvé par un administrateur.</p>
            <p>Vous pouvez maintenant créer des missions.</p>
            </body></html>
        """,
    },
    "document_rejected": {
        "subject": "Document rejeté - Together Platform",
        "body": """
            <html><body>
            <h2>Document Rejeté</h2>
            <p>Bonjour {association_name},</p>
            <p>Votre document a été rejeté.</p>
            <p><strong>Raison:</strong> {rejection_reason}</p>
            <p>Veuillez soumettre un nouveau document corrigé.</p>
            </body></html>
        """,
    },
    "application_approved": {
        "subject": "Candidature acceptée - {mission_name}",
        "body": """
            <html><body>
            <h2>Candidature Acceptée</h2>
            <p>Bonjour {volunteer_name},</p>
            <p>Votre candidature pour la mission "{mission_name}" a été acceptée!</p>
            <p><a href="{frontend_url}/missions/{mission_id}">Voir la mission</a></p>
            </body></html>
        """,
    },
    "application_rejected": {
        "subject": "Candidature refusée - {mission_name}",
        "body": """
            <html><body>
            <h2>Candidature Refusée</h2>
            <p>Bonjour {volunteer_name},</p>
            <p>Votre candidature pour la mission "{mission_name}" a été refusée.</p>
            <p><strong>Raison:</strong> {rejection_reason}</p>
            </body></html>
        """,
    },
    "volunteer_joined": {
        "subject": "Nouveau bénévole - {mission_name}",
        "body": """
            <html><body>
            <h2>Nouveau Bénévole</h2>
            <p>Bonjour {association_name},</p>
            <p>{volunteer_name} a rejoint la mission "{mission_name}".</p>
            <p>Participants actuels: {current_count}/{max_capacity}</p>
            </body></html>
        """,
    },
    "volunteer_left": {
        "subject": "Bénévole retiré - {mission_name}",
        "body": """
            <html><body>
            <h2>Bénévole Retiré</h2>
            <p>Bonjour {association_name},</p>
            <p>{volunteer_name} s'est désisté de la mission "{mission_name}".</p>
            <p>Participants actuels: {current_count}/{max_capacity}</p>
            </body></html>
        """,
    },
    "capacity_reached": {
        "subject": "Capacité minimale atteinte - {mission_name}",
        "body": """
            <html><body>
            <h2>🎉 Capacité Minimale Atteinte!</h2>
            <p>Bonjour {association_name},</p>
            <p>Bonne nouvelle! La mission "{mission_name}" a atteint sa capacité minimale.</p>
            <p>Participants actuels: {current_count}/{max_capacity}</p>
            <p>La mission peut maintenant avoir lieu.</p>
            </body></html>
        """,
    },
    "account_deleted": {
        "subject": "Compte supprimé - Together Platform",
        "body": """
            <html><body>
            <h2>Compte Supprimé</h2>
            <p>Bonjour {username},</p>
            <p>Votre compte Together Platform a été supprimé par un administrateur.</p>
            <p>Si vous pensez qu'il s'agit d'une erreur, contactez le support.</p>
            </body></html>
        """,
    },
    "mission_deleted_association": {
        "subject": "Mission supprimée - {mission_name}",
        "body": """
            <html><body>
            <h2>Mission Supprimée</h2>
            <p>Bonjour {association_name},</p>
            <p>Votre mission "{mission_name}" a été supprimée par un administrateur.</p>
            </body></html>
        """,
    },
    "mission_deleted_volunteer": {
        "subject": "Mission annulée - {mission_name}",
        "body": """
            <html><body>
            <h2>Mission Annulée</h2>
            <p>Bonjour {volunteer_name},</p>
            <p>La mission "{mission_name}" à laquelle vous étiez inscrit a été annulée.</p>
            </body></html>
        """,
    },
    "bulk_message": {
        "subject": "{subject}",
        "body": """
            <html><body>
            <h2>Message concernant "{mission_name}"</h2>
            <p>Bonjour {volunteer_name},</p>
            <p>{custom_message}</p>
            <hr>
            <p><small>Envoyé par {association_name}</small></p>
            </body></html>
        """,
    },
}


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


async def send_notification_email(
    template_name: str, recipient_email: EmailStr, context: dict[str, Any]
) -> None:
    """
    Send notification email using a template.

    Args:
        template_name: Name of the template from EMAIL_TEMPLATES
        recipient_email: Email address to send to
        context: Variables to format into the template

    Returns:
        None

    Raises:
        ValueError: If template_name doesn't exist or email config is invalid
        Exception: If email sending fails
    """
    if template_name not in EMAIL_TEMPLATES:
        raise ValueError(f"Unknown email template: {template_name}")

    template = EMAIL_TEMPLATES[template_name]
    subject = template["subject"].format(**context)
    body = template["body"].format(**context)

    message = MessageSchema(
        subject=subject,
        recipients=[recipient_email],
        body=body,
        subtype=MessageType.html,
    )

    fm = FastMail(get_email_config())
    await fm.send_message(message)
