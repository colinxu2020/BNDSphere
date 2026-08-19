from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Club
from app.models.star_level import StarLevelApplication
from app.repositories.base import RepositoryBase
from app.schemas.star_level import (
    StarLevelApplicationCreate,
    StarLevelApplicationReview,
    StarLevelApplicationUpdate,
)


class StarLevelRepository(
    RepositoryBase[
        StarLevelApplication,
        StarLevelApplicationCreate,
        StarLevelApplicationUpdate,
    ],
):
    model = StarLevelApplication

    async def update_review(
        self,
        application: StarLevelApplication,
        review: StarLevelApplicationReview,
    ) -> StarLevelApplication:
        for field, value in review.model_dump(exclude_unset=True).items():
            setattr(application, field, value)
        self.db.add(application)
        await self.db.flush()
        await self.db.refresh(application)
        return application

    async def list_public(self) -> Page[StarLevelApplication]:
        return cast(
            "Page[StarLevelApplication]",
            await apaginate(
                self.db,
                select(self.model)
                .options(
                    selectinload(self.model.club),
                    selectinload(self.model.academic_term),
                )
                .order_by(self.model.created_at.desc(), self.model.id.desc()),
            ),
        )

    async def list_by_club(self, club: Club) -> Page[StarLevelApplication]:
        return cast(
            "Page[StarLevelApplication]",
            await apaginate(
                self.db,
                select(self.model)
                .where(self.model.club_id == club.id)
                .order_by(self.model.created_at.desc()),
            ),
        )
