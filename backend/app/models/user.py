from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.core.database import Base
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models.clubmember import ClubMember
    from app.models.legal_consent import LegalConsent


class RoleEnum(StrEnum):
    ban = "ban"
    user = "user"
    moderator = "moderator"
    federation_staff = "federation_staff"
    admin = "admin"
    dev = "dev"


_GRADE_LEVEL_MAP: dict[str, int] = {
    "grade_7": 7,
    "grade_8": 8,
    "grade_9": 9,
    "grade_10": 10,
    "grade_11": 11,
    "grade_12": 12,
    "inter_grade_9": 9,
    "inter_grade_10": 10,
    "inter_grade_11": 11,
    "inter_grade_12": 12,
}


class UserGradeEnum(StrEnum):
    grade_7 = "grade_7"
    grade_8 = "grade_8"
    grade_9 = "grade_9"
    grade_10 = "grade_10"
    grade_11 = "grade_11"
    grade_12 = "grade_12"
    inter_grade_9 = "inter_grade_9"
    inter_grade_10 = "inter_grade_10"
    inter_grade_11 = "inter_grade_11"
    inter_grade_12 = "inter_grade_12"

    @property
    def grade_level(self) -> int:
        return _GRADE_LEVEL_MAP[self.value]


class AuditStatusEnum(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
        default=None,
    )
    # Set only by ``ContactVerificationService`` after the address answered a
    # code. An admin can still write ``email`` directly, which deliberately
    # leaves this NULL: an address someone else typed in is not confirmed.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    # E.164, mainland China only today (``+86`` + 11 digits). Unique because
    # it is a recovery and second-factor channel: two accounts sharing one
    # number would make "the number owner" ambiguous at exactly the moment
    # that has to be unambiguous. Unverified numbers are never stored here —
    # the pending value lives on the ``verification_codes`` row until the code
    # is answered — so there is no separate phone_verified flag.
    phone: Mapped[str | None] = mapped_column(
        String(16),
        unique=True,
        default=None,
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Base32 TOTP shared secret. Written when enrollment starts and only
    # *trusted* once ``totp_confirmed_at`` is set: an unconfirmed secret is
    # one nobody has proved their authenticator actually holds, and enforcing
    # it would lock the account out of itself.
    totp_secret: Mapped[str | None] = mapped_column(Text, default=None)
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    # SMS as a second factor, sent to the number in ``phone``. Separate from
    # ``phone_verified_at`` because a verified number is a recovery channel by
    # default and being asked for a code at every login is not.
    sms_two_factor_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    avatar_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)
    description: Mapped[str] = mapped_column(Text, default="这位用户还没有设置简介")
    real_name: Mapped[str | None] = mapped_column(String(20), default=None)
    role: Mapped[RoleEnum] = mapped_column(default=RoleEnum.user)
    wecom_userid: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=None,
    )
    grade: Mapped[UserGradeEnum | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    club_memberships: Mapped[list[ClubMember]] = relationship(back_populates="user")
    legal_consents: Mapped[list[LegalConsent]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )

    @property
    def totp_enabled(self) -> bool:
        """Report whether a TOTP secret exists that an authenticator has answered."""
        return self.totp_secret is not None and self.totp_confirmed_at is not None

    @property
    def sms_two_factor_enabled(self) -> bool:
        """Report whether SMS is armed and still has a number to send to.

        Re-checks ``phone_verified_at`` rather than trusting the flag alone:
        unbinding a number must not leave an account demanding a code that can
        no longer be sent anywhere.
        """
        return (
            self.sms_two_factor_enabled_at is not None
            and self.phone is not None
            and self.phone_verified_at is not None
        )

    @property
    def two_factor_enabled(self) -> bool:
        """Report whether a correct password falls short of logging this account in."""
        return self.totp_enabled or self.sms_two_factor_enabled


class AuditMixin:
    @declared_attr
    @classmethod
    def audit_status(cls) -> Mapped[AuditStatusEnum]:
        return mapped_column(
            default=AuditStatusEnum.pending,
        )

    @declared_attr
    @classmethod
    def auditor_id(cls) -> Mapped[int | None]:
        return mapped_column(
            ForeignKey("users.id"),
            default=None,
        )

    @declared_attr
    @classmethod
    def auditor(cls) -> Mapped[User | None]:
        return relationship("User", foreign_keys=[cls.auditor_id])
