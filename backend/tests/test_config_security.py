import pytest

from app.core.config import Settings


def _base_kwargs():
    return {
        "APP_ENV": "test",
        "LOG_LEVEL": "INFO",
        "AUTH_MODE": "supabase",
        "MOCK_AUTH_ENABLED": "false",
        "ALLOW_MOCK_AUTH_IN_PRODUCTION": "false",
        "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
        "CORS_ORIGINS": "*",
    }


def test_prod_forbids_mock_auth_without_override():
    payload = _base_kwargs()
    payload["APP_ENV"] = "production"
    payload["MOCK_AUTH_ENABLED"] = "true"

    with pytest.raises(ValueError):
        Settings(**payload)


def test_prod_allows_mock_auth_with_explicit_override():
    payload = _base_kwargs()
    payload["APP_ENV"] = "production"
    payload["MOCK_AUTH_ENABLED"] = "true"
    payload["ALLOW_MOCK_AUTH_IN_PRODUCTION"] = "true"

    cfg = Settings(**payload)
    assert cfg.mock_auth_enabled is True
    assert cfg.allow_mock_auth_in_production is True


def test_observability_config_numeric_normalization():
    payload = _base_kwargs()
    payload["SLOW_REQUEST_MS"] = "0"
    payload["OBSERVABILITY_RECENT_ERROR_LIMIT"] = "-1"

    cfg = Settings(**payload)
    assert cfg.slow_request_ms == 1
    assert cfg.observability_recent_error_limit == 1


def test_agora_config_is_optional_and_stripped():
    payload = _base_kwargs()
    payload["AGORA_APP_ID"] = "  agora-app-id  "
    payload["AGORA_APP_CERTIFICATE"] = "  agora-secret  "
    payload["AGORA_AREA"] = "  cn  "
    payload["AGENT_GREETING"] = "  你好，我是小和。  "

    cfg = Settings(**payload)

    assert cfg.agora_app_id == "agora-app-id"
    assert cfg.agora_app_certificate == "agora-secret"
    assert cfg.agora_area == "CN"
    assert cfg.agent_greeting == "你好，我是小和。"


def test_agora_credentials_are_not_required_for_text_only_boot():
    cfg = Settings(**_base_kwargs())

    assert cfg.agora_app_id is None
    assert cfg.agora_app_certificate is None
    assert cfg.agora_area == "US"
    assert cfg.agent_greeting


def test_invalid_agora_area_falls_back_to_us():
    payload = _base_kwargs()
    payload["AGORA_AREA"] = "moon"

    cfg = Settings(**payload)

    assert cfg.agora_area == "US"
