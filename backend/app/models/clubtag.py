from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base

club_tag_table = Table(
    "club_tags",
    Base.metadata,
    Column("club_id", ForeignKey("clubs.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)
