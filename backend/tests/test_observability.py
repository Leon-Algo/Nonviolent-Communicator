import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.observability import observability_registry
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_observability_registry():
    observability_registry.reset()
    yield
    observability_registry.reset()


def test_metrics_endpoint_tracks_status_counts():
    client = TestClient(create_app())

    ok_resp = client.get("/health")
    assert ok_resp.status_code == 200

    not_found_resp = client.get("/path-not-found")
    assert not_found_resp.status_code == 404

    metrics_resp = client.get("/ops/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_requests"] >= 2
    assert metrics["status_counts"].get("200", 0) >= 1
    assert metrics["status_counts"].get("404", 0) >= 1
    assert metrics["slow_request_threshold_ms"] == settings.slow_request_ms
    assert len(metrics["top_endpoints"]) >= 1


def test_server_error_is_aggregated_to_recent_errors():
    app = create_app()

    @app.get("/_boom")
    def _boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_boom")
    assert resp.status_code == 500

    metrics_resp = client.get("/ops/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["server_error_count"] >= 1
    assert len(metrics["recent_errors"]) >= 1
    latest = metrics["recent_errors"][0]
    assert latest["path"] == "/_boom"
    assert latest["status_code"] == 500


def test_request_log_contains_structured_fields(caplog, monkeypatch):
    monkeypatch.setattr(settings, "slow_request_ms", 1)
    caplog.set_level(logging.INFO, logger="nvc.api.request")

    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200

    entries = []
    for record in caplog.records:
        if record.name != "nvc.api.request":
            continue
        try:
            payload = json.loads(record.message)
        except json.JSONDecodeError:
            continue
        entries.append(payload)

    assert len(entries) >= 1
    health_log = next(item for item in entries if item["path"] == "/health")
    assert health_log["method"] == "GET"
    assert health_log["route"] == "/health"
    assert health_log["status_code"] == 200
    assert isinstance(health_log["request_id"], str) and health_log["request_id"]
    assert "latency_ms" in health_log
    assert "is_slow" in health_log
