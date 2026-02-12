import asyncio
from uuid import uuid4

from app.api import deps
from app.core.config import settings
from app.core.security import AuthUser


def test_get_current_user_uses_mock_mode(monkeypatch):
    expected = AuthUser(user_id=uuid4(), email="mock@example.com")
    monkeypatch.setattr(settings, "auth_mode", "mock")
    monkeypatch.setattr(
        deps,
        "parse_mock_bearer_token",
        lambda auth: expected,
    )

    actual = asyncio.run(deps.get_current_user("Bearer mock_token"))
    assert actual == expected


def test_get_current_user_uses_supabase_mode(monkeypatch):
    expected = AuthUser(user_id=uuid4(), email="supabase@example.com")
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "mock_auth_enabled", False)

    async def _verify(_auth: str | None):
        return expected

    monkeypatch.setattr(deps, "verify_supabase_access_token", _verify)

    actual = asyncio.run(deps.get_current_user("Bearer jwt"))
    assert actual == expected


def test_get_current_user_allows_mock_token_when_enabled_even_in_supabase_mode(monkeypatch):
    expected = AuthUser(user_id=uuid4(), email="mock@example.com")
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "mock_auth_enabled", True)
    monkeypatch.setattr(deps, "parse_mock_bearer_token", lambda _auth: expected)

    async def _verify(_auth: str | None):
        raise AssertionError("supabase verifier should not be called for mock token")

    monkeypatch.setattr(deps, "verify_supabase_access_token", _verify)

    actual = asyncio.run(deps.get_current_user("Bearer mock_8a4c3f2a-2f88-4c74-9bc0-3123d26df302"))
    assert actual == expected


def test_get_current_user_does_not_allow_mock_token_when_disabled_in_supabase_mode(
    monkeypatch,
):
    expected = AuthUser(user_id=uuid4(), email="supabase@example.com")
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "mock_auth_enabled", False)

    def _parse_mock(_auth: str | None):
        raise AssertionError("mock parser should not be called when disabled")

    async def _verify(_auth: str | None):
        return expected

    monkeypatch.setattr(deps, "parse_mock_bearer_token", _parse_mock)
    monkeypatch.setattr(deps, "verify_supabase_access_token", _verify)

    actual = asyncio.run(deps.get_current_user("Bearer mock_8a4c3f2a-2f88-4c74-9bc0-3123d26df302"))
    assert actual == expected
