from datetime import date

from pydantic import BaseModel, Field


class WeeklyProgressResponse(BaseModel):
    week_start: date
    practice_count: int = Field(ge=0)
    summary_count: int = Field(ge=0)
    real_world_used_count: int = Field(ge=0)
    avg_outcome_score: float = Field(ge=0, le=5)
