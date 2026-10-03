"""Guards on how admin club import may backdate a club's created_at."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.club import ClubCategoryEnum
from app.schemas.club import AdminClubCreate
from app.services.errors import BadRequestError


def admin_club_create(created_at: datetime) -> AdminClubCreate:
    return AdminClubCreate(
        name="Historic Club",
        category=ClubCategoryEnum.sports,
        summary="imported",
        description="imported from the old system",
        logo_uri=None,
        created_at=created_at,
    )


def test_admin_club_create_rejects_future_created_at() -> None:
    with pytest.raises(BadRequestError) as exc_info:
        admin_club_create(datetime.now(UTC) + timedelta(days=1))

    assert exc_info.value.error_code == "CLUB_CREATED_AT_IN_FUTURE"


def test_admin_club_create_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        admin_club_create(datetime(2020, 1, 1))  # noqa: DTZ001


def test_admin_club_create_accepts_past_created_at() -> None:
    club = admin_club_create(datetime(2020, 1, 1, tzinfo=UTC))

    assert club.created_at.year == 2020
