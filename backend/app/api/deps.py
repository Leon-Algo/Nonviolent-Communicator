from fastapi import Header

from app.core.config import settings
from app.core.security import AuthUser, parse_mock_bearer_token
from app.core.supabase_auth import verify_supabase_access_token


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    token_is_mock = isinstance(authorization, str) and authorization.strip().startswith("Bearer mock_")

    # Allow explicit mock token in any auth mode when mock is enabled.
    if token_is_mock and settings.mock_auth_enabled:
        return parse_mock_bearer_token(authorization)

    if settings.auth_mode == "mock":
        return parse_mock_bearer_token(authorization)
    if settings.auth_mode == "supabase":
        return await verify_supabase_access_token(authorization)

    if settings.mock_auth_enabled:
        return parse_mock_bearer_token(authorization)
    return await verify_supabase_access_token(authorization)

