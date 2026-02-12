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
