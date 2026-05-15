from app.models.academic_term import AcademicTerm
from app.models.activity import Activity
from app.models.activity_participator import activity_participator_table  # noqa: F401
from app.models.club import Club
from app.models.clubmember import ClubMember
from app.models.clubtag import club_tag_table  # noqa: F401
from app.models.general_activity import GeneralActivity
from app.models.tag import Tag
from app.models.user import User

__all__ = [
    "AcademicTerm",
    "Activity",
    "Club",
    "ClubMember",
    "GeneralActivity",
    "Tag",
    "User",
]
