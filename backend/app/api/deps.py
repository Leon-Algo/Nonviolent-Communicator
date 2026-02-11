from fastapi import Header

from app.core.config import settings
from app.core.security import AuthUser, parse_mock_bearer_token
from app.core.supabase_auth import verify_supabase_access_token


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if settings.auth_mode == "mock":
        return parse_mock_bearer_token(authorization)
    if settings.auth_mode == "supabase":
        return await verify_supabase_access_token(authorization)

    if settings.mock_auth_enabled:
        return parse_mock_bearer_token(authorization)
    return await verify_supabase_access_token(authorization)
