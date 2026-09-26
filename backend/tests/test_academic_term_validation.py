import pytest
from pydantic import ValidationError

from app.schemas.academic_terms import AcademicTermCreate, AcademicTermUpdate
from app.services.errors import BadRequestError


def test_update_may_omit_term_name() -> None:
    update = AcademicTermUpdate()

    assert "term_name" not in update.model_fields_set


def test_update_rejects_an_explicit_null_term_name() -> None:
    with pytest.raises(BadRequestError) as exc_info:
        AcademicTermUpdate(term_name=None)

    assert exc_info.value.error_code == "NON_NULLABLE_FIELD_NULL"


@pytest.mark.parametrize("term_name", ["", "   "])
def test_term_name_rejects_blank_text(term_name: str) -> None:
    with pytest.raises(ValidationError):
        AcademicTermUpdate(term_name=term_name)


def test_create_still_allows_an_omitted_generated_name() -> None:
    term = AcademicTermCreate(
        start_date="2026-09-01",
        end_date="2027-01-31",
        is_current=False,
    )

    assert term.term_name is None
