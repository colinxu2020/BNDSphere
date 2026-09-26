from collections.abc import Collection
from dataclasses import dataclass

from app.models.club import Club
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.services.errors import ResourceForbiddenError


@dataclass(frozen=True)
class RoleCapabilities:
    allowed_roles: frozenset[RoleEnum]
    bypass_role_checks: bool = False


# Role inheritance is explicit, not an ordinal hierarchy. Banned users are
# rejected before consulting capabilities, including club membership checks.
ROLE_CAPABILITIES = {
    RoleEnum.ban: RoleCapabilities(frozenset()),
    RoleEnum.user: RoleCapabilities(frozenset({RoleEnum.user})),
    RoleEnum.moderator: RoleCapabilities(frozenset({RoleEnum.moderator})),
    RoleEnum.federation_staff: RoleCapabilities(
        frozenset({RoleEnum.federation_staff, RoleEnum.moderator}),
    ),
    RoleEnum.admin: RoleCapabilities(frozenset(), bypass_role_checks=True),
    RoleEnum.dev: RoleCapabilities(frozenset(), bypass_role_checks=True),
}


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
        capabilities = ROLE_CAPABILITIES[user.role]
        if capabilities.bypass_role_checks or not capabilities.allowed_roles.isdisjoint(
            allowed_roles,
        ):
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
        if ROLE_CAPABILITIES[user.role].bypass_role_checks:
            return
        if membership is not None and membership.membership in allowed_roles:
            return
        raise ResourceForbiddenError(
            "error.club.role_not_allowed",
            "CLUB_ROLE_NOT_ALLOWED",
            {"club_id": club.id},
        ) from None
