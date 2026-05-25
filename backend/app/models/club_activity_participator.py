from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base

club_activity_participator_table = Table(
    "club_activity_participators",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("club_activity_id", ForeignKey("club_activities.id"), primary_key=True),
)
