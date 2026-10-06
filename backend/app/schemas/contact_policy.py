from datetime import date
from typing import Literal

from pydantic import BaseModel


class ContactPolicyStatus(BaseModel):
    version: date
    accepted: bool


class ContactPolicyAcceptance(BaseModel):
    version: date
    accepted: Literal[True]
