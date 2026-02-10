from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(slots=True)
class AuthUser:
    user_id: str


def parse_mock_bearer_token(authorization: str | None) -> AuthUser:
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
    if not token.startswith("mock_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid mock token",
        )

    user_id = token.removeprefix("mock_").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid mock token user id",
        )

    return AuthUser(user_id=user_id)
