from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status


@dataclass(slots=True)
class AuthUser:
    user_id: UUID
    email: str | None = None
    display_name: str | None = None


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization header",
        )

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid Authorization header",
        )

    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return token


def parse_mock_bearer_token(authorization: str | None) -> AuthUser:
    token = extract_bearer_token(authorization)
    if not token.startswith("mock_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid mock token",
        )

    user_id_raw = token.removeprefix("mock_").strip()
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid mock token user id",
        )

    try:
        user_id = UUID(user_id_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="mock user id must be a valid UUID",
        ) from exc

    return AuthUser(
        user_id=user_id,
        email=f"{user_id}@mock.local",
        display_name="Mock User",
    )
