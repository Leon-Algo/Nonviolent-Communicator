from fastapi import Header

from app.core.config import settings
from app.core.security import AuthUser, parse_mock_bearer_token


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if settings.mock_auth_enabled:
        return parse_mock_bearer_token(authorization)

    # Placeholder for real auth integration.
    return parse_mock_bearer_token(authorization)
