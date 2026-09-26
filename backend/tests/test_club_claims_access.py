"""Guards on the club claim flow: who may review, and how clubs may be backdated."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.api.dependencies import RoleChecker
from app.main import app
from app.models.club import ClubCategoryEnum
from app.models.user import RoleEnum
from app.schemas.club import AdminClubCreate
from app.services.errors import BadRequestError


def club_claim_routes() -> list[APIRoute]:
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and "/club-claims" in route.path
    ]


def required_role_sets(route: APIRoute) -> list[list[RoleEnum]]:
    return [
        dependency.call.allowed_roles
        for dependency in route.dependant.dependencies
        if isinstance(dependency.call, RoleChecker)
    ]


def test_club_claim_routes_are_admin_only() -> None:
    routes = club_claim_routes()
    assert routes, "club claim routes are not registered"
    for route in routes:
        assert [RoleEnum.admin] in required_role_sets(route), (
            f"{route.path} must be admin-only: approving a claim appoints a president"
        )


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
