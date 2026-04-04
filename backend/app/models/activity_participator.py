from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base


activity_participator_table = Table(
    "activity_participators",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("activity_id", ForeignKey("activities.id"), primary_key=True),
)
