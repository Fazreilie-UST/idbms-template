import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import security_logger


class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> None:
        if not settings.SMTP_HOST:
            raise RuntimeError("SMTP_HOST is not configured")

        message = EmailMessage()
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()

                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

                smtp.send_message(message)

        except Exception:
            security_logger.exception("Failed to send email to %s", to_email)
            raise

    @staticmethod
    def send_password_reset_email(
        to_email: str,
        reset_link: str,
    ) -> None:
        subject = "Reset your NPI DBMS password"

        body = f"""
            Hello,

            We received a request to reset your NPI DBMS password.

            Click the link below to reset your password:

            {reset_link}

            This link will expire soon.

            If you did not request this, you can ignore this email.

            Regards,
            NPI DBMS
        """

        EmailService.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
        )