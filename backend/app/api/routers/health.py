from fastapi import APIRouter

from app.core.config import settings
from app.core.observability import observability_registry
from app.schemas.common import HealthResponse, ObservabilityMetricsResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app_env=settings.app_env)


@router.get("/ops/metrics", response_model=ObservabilityMetricsResponse)
def observability_metrics() -> ObservabilityMetricsResponse:
    payload = observability_registry.snapshot(
        slow_request_threshold_ms=settings.slow_request_ms
    )
    return ObservabilityMetricsResponse.model_validate(payload)
