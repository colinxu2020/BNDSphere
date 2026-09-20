import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.settings import SmtpSettings, smtp_settings, web_settings
from app.models.verification_code import VerificationPurposeEnum
from app.services.errors import NotificationChannelUnavailableError

logger = logging.getLogger(__name__)

# Purpose-specific wording, not one generic "your code is". A recipient who
# was talked into requesting a code needs the mail itself to say what
# answering it will do; "验证码" alone is what makes that phone call work.
_MESSAGES: dict[VerificationPurposeEnum, tuple[str, str]] = {
    VerificationPurposeEnum.bind: (
        "BNDSphere 邮箱验证码",
        """你好,

你的 BNDSphere 邮箱验证码是: {code}

该验证码用于确认这个邮箱属于你, 在 {minutes} 分钟内有效。
如果这不是你本人的操作, 请忽略这封邮件。

—— BNDSphere
""",
    ),
    VerificationPurposeEnum.password_reset: (
        "BNDSphere 密码重置验证码",
        """你好,

你的 BNDSphere 密码重置验证码是: {code}

输入这个验证码的人可以重新设置你的账号密码, 请不要转发给任何人。
验证码在 {minutes} 分钟内有效。

如果这不是你本人的操作, 请忽略这封邮件并考虑修改密码 —— 有人知道你的用户名。

—— BNDSphere
""",
    ),
}


def _send_blocking(
    settings: SmtpSettings,
    to: str,
    code: str,
    minutes: int,
    purpose: VerificationPurposeEnum,
) -> None:
    """Build and deliver one message. Blocking; call it off the event loop."""
    subject, body = _MESSAGES[purpose]
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = to
    message.set_content(body.format(code=code, minutes=minutes))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


class EmailSender:
    """Deliver verification codes over SMTP.

    ``smtplib`` rather than an async mail client: it is in the standard
    library, and one short-lived connection per code is nothing next to the
    per-account send budget. The blocking call is pushed to a worker thread so
    it cannot stall the event loop while a slow relay does its handshake.
    """

    async def send_code(
        self,
        to: str,
        code: str,
        minutes: int,
        purpose: VerificationPurposeEnum = VerificationPurposeEnum.bind,
    ) -> None:
        settings = smtp_settings()
        if not settings.configured:
            if web_settings().debug:
                # Local development without a relay: the code goes to the log
                # so the flow is still walkable end to end.
                logger.warning(
                    "SMTP not configured; verification code for %s is %s",
                    to,
                    code,
                )
                return
            raise NotificationChannelUnavailableError("email")

        try:
            await asyncio.to_thread(
                _send_blocking,
                settings,
                to,
                code,
                minutes,
                purpose,
            )
        except (smtplib.SMTPException, OSError) as err:
            # The address and the relay's complaint are useful in the log and
            # harmful in the response: a caller must not be able to use
            # delivery errors to probe which addresses exist elsewhere.
            logger.exception("SMTP delivery to %s failed", to)
            raise NotificationChannelUnavailableError("email") from err
