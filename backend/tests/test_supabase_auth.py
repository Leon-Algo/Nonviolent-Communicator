import asyncio
from uuid import uuid4

from fastapi import HTTPException

from app.core.security import AuthUser
from app.core.supabase_auth import verify_supabase_access_token
from app.core import supabase_auth


def test_verify_supabase_access_token_uses_jwks_when_available(monkeypatch):
    expected = AuthUser(user_id=uuid4(), email="user@example.com", display_name="User")

    monkeypatch.setattr(
        supabase_auth,
        "_decode_token_with_jwks",
        lambda token: expected,
    )

    async def _fallback(_token: str):
        raise AssertionError("fallback should not be called when jwks succeeds")

    monkeypatch.setattr(supabase_auth, "_fetch_user_from_supabase", _fallback)

    actual = asyncio.run(verify_supabase_access_token("Bearer sample-token"))
    assert actual == expected


def test_verify_supabase_access_token_falls_back_to_user_endpoint(monkeypatch):
    expected = AuthUser(user_id=uuid4(), email="fallback@example.com", display_name="Fallback")

    def _decode_fail(_token: str):
        raise ValueError("decode failed")

    async def _fallback(_token: str):
        return expected

    monkeypatch.setattr(supabase_auth, "_decode_token_with_jwks", _decode_fail)
    monkeypatch.setattr(supabase_auth, "_fetch_user_from_supabase", _fallback)

    actual = asyncio.run(verify_supabase_access_token("Bearer sample-token"))
    assert actual == expected


def test_verify_supabase_access_token_requires_bearer_header():
    try:
        asyncio.run(verify_supabase_access_token(None))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401
