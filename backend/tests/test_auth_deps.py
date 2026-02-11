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

    async def _verify(_auth: str | None):
        return expected

    monkeypatch.setattr(deps, "verify_supabase_access_token", _verify)

    actual = asyncio.run(deps.get_current_user("Bearer jwt"))
    assert actual == expected
