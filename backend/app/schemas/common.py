from pydantic import BaseModel
from pydantic import Field
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    app_env: str


class EndpointCountItem(BaseModel):
    endpoint: str
    count: int = Field(ge=0)


class RecentErrorItem(BaseModel):
    timestamp: datetime
    request_id: str
    method: str
    path: str
    route: str
    status_code: int = Field(ge=500)
    latency_ms: float = Field(ge=0)


class ObservabilityMetricsResponse(BaseModel):
    started_at: datetime
    total_requests: int = Field(ge=0)
    status_counts: dict[str, int]
    avg_latency_ms: float = Field(ge=0)
    max_latency_ms: float = Field(ge=0)
    slow_request_count: int = Field(ge=0)
    server_error_count: int = Field(ge=0)
    slow_request_threshold_ms: int = Field(ge=1)
    top_endpoints: list[EndpointCountItem]
    recent_errors: list[RecentErrorItem]
