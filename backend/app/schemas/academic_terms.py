from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.core import constants


class AcademicTermInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    term_name: str = Field(max_length=constants.ACADEMIC_TERM_MAX_LENGTH)
    start_date: date = Field(...)
    end_date: date = Field(...)


class AcademicTermCreate(BaseModel):
    term_name: str | None = Field(None, max_length=constants.ACADEMIC_TERM_MAX_LENGTH)
    start_date: date = Field(...)
    end_date: date = Field(...)


class AcademicTermUpdate(BaseModel):
    term_name: str | None = Field(None, max_length=constants.ACADEMIC_TERM_MAX_LENGTH)
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)
