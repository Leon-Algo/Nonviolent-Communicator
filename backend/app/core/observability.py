from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class RecentErrorEvent:
    timestamp: datetime
    request_id: str
    method: str
    path: str
    route: str
    status_code: int
    latency_ms: float


class ObservabilityRegistry:
    def __init__(self, max_recent_errors: int = 20) -> None:
        self._lock = Lock()
        self._max_recent_errors = max(1, max_recent_errors)
        self._recent_errors: deque[RecentErrorEvent] = deque(
            maxlen=self._max_recent_errors
        )
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._started_at = _utc_now()
            self._total_requests = 0
            self._total_latency_ms = 0.0
            self._max_latency_ms = 0.0
            self._slow_request_count = 0
            self._server_error_count = 0
            self._status_counts: Counter[str] = Counter()
            self._endpoint_counts: Counter[str] = Counter()
            self._recent_errors.clear()

    def configure(self, *, max_recent_errors: int | None = None) -> None:
        with self._lock:
            if max_recent_errors is None:
                return
            normalized = max(1, max_recent_errors)
            if normalized == self._max_recent_errors:
                return
            self._max_recent_errors = normalized
            self._recent_errors = deque(self._recent_errors, maxlen=normalized)

    def observe(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        route: str,
        status_code: int,
        latency_ms: float,
        is_slow: bool,
    ) -> None:
        endpoint_key = f"{method} {route}"
        with self._lock:
            self._total_requests += 1
            self._total_latency_ms += latency_ms
            self._max_latency_ms = max(self._max_latency_ms, latency_ms)
            self._status_counts[str(status_code)] += 1
            self._endpoint_counts[endpoint_key] += 1
            if is_slow:
                self._slow_request_count += 1
            if status_code >= 500:
                self._server_error_count += 1
                self._recent_errors.append(
                    RecentErrorEvent(
                        timestamp=_utc_now(),
                        request_id=request_id,
                        method=method,
                        path=path,
                        route=route,
                        status_code=status_code,
                        latency_ms=latency_ms,
                    )
                )

    def snapshot(self, *, slow_request_threshold_ms: int, top_n: int = 10) -> dict:
        with self._lock:
            avg_latency = (
                self._total_latency_ms / self._total_requests
                if self._total_requests > 0
                else 0.0
            )
            top_endpoints = [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in self._endpoint_counts.most_common(max(1, top_n))
            ]
            recent_errors = [
                {
                    "timestamp": event.timestamp,
                    "request_id": event.request_id,
                    "method": event.method,
                    "path": event.path,
                    "route": event.route,
                    "status_code": event.status_code,
                    "latency_ms": round(event.latency_ms, 2),
                }
                for event in reversed(self._recent_errors)
            ]
            return {
                "started_at": self._started_at,
                "total_requests": self._total_requests,
                "status_counts": dict(self._status_counts),
                "avg_latency_ms": round(avg_latency, 2),
                "max_latency_ms": round(self._max_latency_ms, 2),
                "slow_request_count": self._slow_request_count,
                "server_error_count": self._server_error_count,
                "slow_request_threshold_ms": slow_request_threshold_ms,
                "top_endpoints": top_endpoints,
                "recent_errors": recent_errors,
            }


observability_registry = ObservabilityRegistry()

