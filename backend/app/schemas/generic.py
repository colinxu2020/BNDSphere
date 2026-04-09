from pydantic import BaseModel


class IdMixin(BaseModel):
    id: int
