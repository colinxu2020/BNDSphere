from datetime import date
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.core import constants
from app.schemas.generic import IdMixin, ensure_non_nullable_fields_present

TermName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=constants.ACADEMIC_TERM_MAX_LENGTH,
    ),
]


class AcademicTermInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    term_name: str = Field(max_length=constants.ACADEMIC_TERM_MAX_LENGTH)
    start_date: date = Field(...)
    end_date: date = Field(...)
    is_current: bool = Field(...)


class AcademicTermCreate(BaseModel):
    term_name: TermName | None = None
    start_date: date = Field(...)
    end_date: date = Field(...)
    is_current: bool = Field(...)


class AcademicTermUpdate(BaseModel):
    term_name: TermName | None = None
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> Self:
        ensure_non_nullable_fields_present(self, {"term_name"})
        return self
