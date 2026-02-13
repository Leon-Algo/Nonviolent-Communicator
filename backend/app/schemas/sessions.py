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


class SessionHistoryListItem(BaseModel):
    session_id: UUID
    scene_id: UUID
    scene_title: str
    state: SessionState
    current_turn: int = Field(ge=0)
    target_turns: int = Field(ge=5, le=8)
    created_at: datetime
    ended_at: datetime | None = None
    last_user_message: str | None = None
    last_assistant_message: str | None = None
    last_overall_score: int | None = Field(default=None, ge=0, le=100)
    last_risk_level: RiskLevel | None = None
    has_summary: bool
    has_reflection: bool


class SessionHistoryListResponse(BaseModel):
    items: list[SessionHistoryListItem]
    limit: int = Field(ge=1, le=50)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


class SessionHistoryFeedback(BaseModel):
    overall_score: int | None = Field(default=None, ge=0, le=100)
    risk_level: RiskLevel | None = None
    ofnr: OfnrFeedback | None = None
    next_best_sentence: str | None = None


class SessionHistoryTurn(BaseModel):
    turn: int = Field(ge=1)
    user_message_id: UUID
    user_content: str
    assistant_message_id: UUID | None = None
    assistant_content: str | None = None
    feedback: SessionHistoryFeedback | None = None


class SessionHistoryScene(BaseModel):
    scene_id: UUID
    title: str
    goal: str
    context: str
    template_id: str


class SessionHistoryReflection(BaseModel):
    reflection_id: UUID
    used_in_real_world: bool
    outcome_score: int | None = Field(default=None, ge=1, le=5)
    blocker_code: str | None = None
    blocker_note: str | None = None
    created_at: datetime


class SessionHistoryDetailResponse(BaseModel):
    session_id: UUID
    scene: SessionHistoryScene
    state: SessionState
    current_turn: int = Field(ge=0)
    target_turns: int = Field(ge=5, le=8)
    created_at: datetime
    ended_at: datetime | None = None
    turns: list[SessionHistoryTurn]
    summary: SummaryCreateResponse | None = None
    reflection: SessionHistoryReflection | None = None
