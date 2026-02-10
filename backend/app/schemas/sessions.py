from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SessionState(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class OfnrStatus(StrEnum):
    MISSING = "MISSING"
    WEAK = "WEAK"
    GOOD = "GOOD"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RewriteStyle(StrEnum):
    NEUTRAL = "NEUTRAL"


class SessionCreateRequest(BaseModel):
    scene_id: UUID
    target_turns: int = Field(ge=5, le=8)


class SessionCreateResponse(BaseModel):
    session_id: UUID
    state: SessionState
    current_turn: int
    created_at: datetime


class MessageCreateRequest(BaseModel):
    client_message_id: UUID
    content: str = Field(min_length=1, max_length=4000)


class AssistantMessage(BaseModel):
    message_id: UUID
    content: str


class OfnrDimensionFeedback(BaseModel):
    status: OfnrStatus
    reason: str
    suggestion: str


class OfnrFeedback(BaseModel):
    observation: OfnrDimensionFeedback
    feeling: OfnrDimensionFeedback
    need: OfnrDimensionFeedback
    request: OfnrDimensionFeedback


class FeedbackPayload(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    ofnr: OfnrFeedback
    next_best_sentence: str


class MessageCreateResponse(BaseModel):
    user_message_id: UUID
    assistant_message: AssistantMessage
    feedback: FeedbackPayload
    turn: int = Field(ge=1)


class RewriteCreateRequest(BaseModel):
    source_message_id: UUID
    rewrite_style: RewriteStyle


class RewriteCreateResponse(BaseModel):
    rewrite_id: UUID
    rewritten_content: str


class SummaryCreateResponse(BaseModel):
    summary_id: UUID
    opening_line: str
    request_line: str
    fallback_line: str
    risk_triggers: list[str]
    created_at: datetime
