from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class BlockerCode(StrEnum):
    NO_CHANCE = "NO_CHANCE"
    EMOTION_SPIKE = "EMOTION_SPIKE"
    POWER_GAP = "POWER_GAP"
    WORDING_ISSUE = "WORDING_ISSUE"
    OTHER = "OTHER"


class ReflectionCreateRequest(BaseModel):
    session_id: UUID
    used_in_real_world: bool
    outcome_score: int | None = Field(default=None, ge=1, le=5)
    blocker_code: BlockerCode | None = None
    blocker_note: str | None = Field(default=None, max_length=500)


class ReflectionCreateResponse(BaseModel):
    reflection_id: UUID
    created_at: datetime
