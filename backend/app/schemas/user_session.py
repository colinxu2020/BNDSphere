from datetime import datetime

from pydantic import BaseModel


class UserSessionCreate(BaseModel):
    user_id: int
    token_hash: str
    expires_at: datetime
