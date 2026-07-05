from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceSessionStartRequest(BaseModel):
    scene_id: UUID
    target_turns: int = Field(default=6, ge=5, le=8)


class VoiceSessionStartResponse(BaseModel):
    session_id: UUID
    app_id: str
    token: str
    uid: str
    channel_name: str
    agent_uid: str
    agent_id: str
    expires_at: datetime


class VoiceSessionStopResponse(BaseModel):
    session_id: UUID
    status: str


class VoiceTranscriptTurn(BaseModel):
    role: Literal["USER", "ASSISTANT"]
    content: str = Field(min_length=1, max_length=4000)
    external_turn_id: str = Field(min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceTranscriptSyncRequest(BaseModel):
    turns: list[VoiceTranscriptTurn] = Field(min_length=1, max_length=50)


class VoiceTranscriptSyncResponse(BaseModel):
    session_id: UUID
    inserted_count: int = Field(ge=0)
    current_turn: int = Field(ge=0)
    state: str
