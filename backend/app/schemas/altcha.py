from enum import StrEnum

from pydantic import BaseModel, Field


class AltchaPurpose(StrEnum):
    login = "login"
    register = "register"


type AltchaDataValue = str | int | bool | None


class AltchaChallengeParameters(BaseModel):
    algorithm: str
    nonce: str
    salt: str
    cost: int
    key_length: int = Field(alias="keyLength")
    key_prefix: str = Field(alias="keyPrefix")
    key_signature: str | None = Field(None, alias="keySignature")
    memory_cost: int | None = Field(None, alias="memoryCost")
    parallelism: int | None = None
    expires_at: int = Field(alias="expiresAt")
    data: dict[str, AltchaDataValue]


class AltchaChallenge(BaseModel):
    parameters: AltchaChallengeParameters
    signature: str
