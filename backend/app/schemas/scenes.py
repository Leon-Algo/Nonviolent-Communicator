from typing import Annotated
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

PainPoint = Annotated[str, Field(min_length=1, max_length=80)]


class TemplateId(StrEnum):
    PEER_FEEDBACK = "PEER_FEEDBACK"
    MANAGER_ALIGNMENT = "MANAGER_ALIGNMENT"
    CROSS_TEAM_CONFLICT = "CROSS_TEAM_CONFLICT"
    CUSTOM = "CUSTOM"


class CounterpartyRole(StrEnum):
    PEER = "PEER"
    MANAGER = "MANAGER"
    REPORT = "REPORT"
    CLIENT = "CLIENT"
    OTHER = "OTHER"


class RelationshipLevel(StrEnum):
    SMOOTH = "SMOOTH"
    NEUTRAL = "NEUTRAL"
    TENSE = "TENSE"


class PowerDynamic(StrEnum):
    USER_HIGHER = "USER_HIGHER"
    PEER_LEVEL = "PEER_LEVEL"
    COUNTERPART_HIGHER = "COUNTERPART_HIGHER"


class SceneCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    template_id: TemplateId
    counterparty_role: CounterpartyRole
    relationship_level: RelationshipLevel
    goal: str = Field(min_length=1, max_length=240)
    pain_points: list[PainPoint] = Field(default_factory=list, max_length=5)
    context: str = Field(min_length=1, max_length=1200)
    power_dynamic: PowerDynamic


class SceneCreateResponse(BaseModel):
    scene_id: UUID
    status: str
    created_at: datetime
