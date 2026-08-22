from typing import Self

from pydantic import Field, model_validator

from app.core import constants
from app.models.verifications.verification_common import VerificationStatusEnum
from app.schemas.verifications.verification_common import RequestVerifyPublic
from app.services.errors import BadRequestError


class JointActivityFinalVerification(RequestVerifyPublic):
    final_score: int = Field(
        0,
        ge=0,
        le=constants.JOINT_ACTIVITY_MAX_FINAL_SCORE,
    )

    @model_validator(mode="after")
    def validate_approved_score(self) -> Self:
        if (
            self.verification_status == VerificationStatusEnum.approved
            and self.final_score < constants.JOINT_ACTIVITY_MIN_FINAL_SCORE
        ):
            raise BadRequestError(
                "error.joint_activity.invalid_final_score",
                "JOINT_ACTIVITY_INVALID_FINAL_SCORE",
                {
                    "min_score": constants.JOINT_ACTIVITY_MIN_FINAL_SCORE,
                    "max_score": constants.JOINT_ACTIVITY_MAX_FINAL_SCORE,
                },
            )
        return self
