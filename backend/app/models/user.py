from enum import Enum
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.settings import settings


class RoleEnum(str, Enum):
    ban = "ban"
    user = "user"
    union_of_associations = "union of associations"
    admin = "admin"
    dev = "dev"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(settings.max_username_length), unique=True, index=True
    )
    email: Mapped[str | None] = mapped_column(
        String(settings.max_email_length), unique=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_uri: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(settings.max_description_length))
    real_name: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[RoleEnum] = mapped_column()
    wecom_userid: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
