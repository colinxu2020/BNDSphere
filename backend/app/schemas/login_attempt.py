from pydantic import BaseModel


class LoginAttemptCreate(BaseModel):
    username: str
    ip: str | None = None
    successful: bool
