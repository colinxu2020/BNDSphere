from collections.abc import Collection

from app.models.club import Club
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.services.errors import ResourceForbiddenError


class AccessPolicy:
    @staticmethod
    def ensure_user_active(user: User) -> None:
        if user.role == RoleEnum.ban:
            raise ResourceForbiddenError(
                "error.user.banned",
                "USER_BANNED",
                {"user_id": user.id},
            ) from None

    @staticmethod
    def ensure_role_allowed(
        user: User,
        allowed_roles: Collection[RoleEnum],
    ) -> None:
        AccessPolicy.ensure_user_active(user)
        if user.role in allowed_roles or user.role == RoleEnum.dev:
            return
        raise ResourceForbiddenError(
            "error.role.not_allowed",
            "ROLE_NOT_ALLOWED",
        ) from None

    @staticmethod
    def ensure_club_role_allowed(
        user: User,
        club: Club,
        membership: ClubMember | None,
        allowed_roles: Collection[ClubMembershipEnum],
    ) -> None:
        AccessPolicy.ensure_user_active(user)
        if user.role in (RoleEnum.dev, RoleEnum.admin):
            return
        if membership is not None and membership.membership in allowed_roles:
            return
        raise ResourceForbiddenError(
            "error.club.role_not_allowed",
            "CLUB_ROLE_NOT_ALLOWED",
            {"club_id": club.id},
        ) from None
