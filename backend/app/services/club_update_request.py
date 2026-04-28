from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models.club import Club
from app.models.club_update_request import ClubUpdateRequest
from app.models.user import AuditStatusEnum, User
from app.schemas.club import ClubUpdate
from app.services.base import ServiceBase
from app.services.errors import ClubUpdateRequestNotFoundError, ResourceForbiddenError


class ClubUpdateRequestService(
    ServiceBase[ClubUpdateRequest, ClubUpdate, ClubUpdate],
):
    model = ClubUpdateRequest

    async def get_pending_by_club(self, club_id: int) -> ClubUpdateRequest | None:
        """Get the pending update request for a specific club, if any."""
        stmt = select(self.model).where(
            self.model.club_id == club_id,
            self.model.audit_status == AuditStatusEnum.pending,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_or_update_request(
        self,
        club: Club,
        user: User,
        obj_in: ClubUpdate,
    ) -> ClubUpdateRequest:
        """Create a new update request, or update the existing pending one."""
        existing = await self.get_pending_by_club(club.id)
        if existing is not None:
            for field, value in obj_in.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            existing.requester_id = user.id
            self.db.add(existing)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        db_obj = ClubUpdateRequest(
            club_id=club.id,
            requester_id=user.id,
            **obj_in.model_dump(),
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def get_pending_requests(self) -> Page[ClubUpdateRequest]:
        """Get all pending update requests (paginated)."""
        stmt = (
            select(self.model)
            .where(self.model.audit_status == AuditStatusEnum.pending)
            .order_by(self.model.created_at.desc())
        )
        return cast("Page[ClubUpdateRequest]", await apaginate(self.db, stmt))

    async def get_requests_by_club(self, club_id: int) -> Page[ClubUpdateRequest]:
        """Get all update requests for a specific club (paginated)."""
        stmt = (
            select(self.model)
            .where(self.model.club_id == club_id)
            .order_by(self.model.created_at.desc())
        )
        return cast("Page[ClubUpdateRequest]", await apaginate(self.db, stmt))

    async def ensure_request(self, request_id: int) -> ClubUpdateRequest:
        """Get a request by id, raise if not found."""
        request = await self.get(request_id)
        if request is None:
            raise ClubUpdateRequestNotFoundError(request_id)
        return request

    async def audit(
        self,
        request: ClubUpdateRequest,
        audit_status: AuditStatusEnum,
        auditor: User,
        club: Club,
    ) -> ClubUpdateRequest:
        """Audit a pending request. If approved, apply changes to the club."""
        if request.audit_status != AuditStatusEnum.pending:
            raise ResourceForbiddenError(
                message_key="error.club.update_request_already_reviewed",
                error_code="UPDATE_REQUEST_ALREADY_REVIEWED",
                details={"request_id": request.id},
            )

        request.audit_status = audit_status
        request.auditor_id = auditor.id

        if audit_status == AuditStatusEnum.approved:
            club.summary = request.summary
            club.description = request.description
            club.logo_uri = request.logo_uri
            self.db.add(club)

        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request
