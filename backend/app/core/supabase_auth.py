from uuid import UUID

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.config import settings
from app.core.security import AuthUser, extract_bearer_token

SUPPORTED_JWT_ALGS = ["RS256", "ES256", "EdDSA"]
_jwks_client: PyJWKClient | None = None


def _resolve_issuer() -> str:
    if settings.jwt_issuer:
        return settings.jwt_issuer.rstrip("/")
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="supabase auth issuer is not configured",
        )
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _resolve_jwks_url() -> str:
    return f"{_resolve_issuer()}/.well-known/jwks.json"


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(_resolve_jwks_url())
    return _jwks_client


def _auth_user_from_claims(claims: dict) -> AuthUser:
    sub = claims.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token subject",
        )
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token subject",
        ) from exc

    email = claims.get("email")
    display_name = claims.get("user_metadata", {}).get("full_name") if isinstance(
        claims.get("user_metadata"), dict
    ) else None

    return AuthUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        display_name=display_name if isinstance(display_name, str) else None,
    )


def _decode_token_with_jwks(token: str) -> AuthUser:
    issuer = _resolve_issuer()
    jwk_client = _get_jwks_client()
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=SUPPORTED_JWT_ALGS,
        audience=settings.jwt_audience,
        issuer=issuer,
        options={"require": ["sub", "exp", "iat"]},
    )
    return _auth_user_from_claims(claims)


async def _fetch_user_from_supabase(token: str) -> AuthUser:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="supabase auth url is not configured",
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    apikey = settings.supabase_anon_key or settings.supabase_service_role_key
    headers = {"Authorization": f"Bearer {token}"}
    if apikey:
        headers["apikey"] = apikey

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="failed to validate access token",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
        )

    payload = response.json()
    user_id_raw = payload.get("id")
    try:
        user_id = UUID(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token subject",
        ) from exc

    user_metadata = payload.get("user_metadata")
    display_name = (
        user_metadata.get("full_name")
        if isinstance(user_metadata, dict)
        else None
    )
    email = payload.get("email")

    return AuthUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        display_name=display_name if isinstance(display_name, str) else None,
    )


async def verify_supabase_access_token(authorization: str | None) -> AuthUser:
    token = extract_bearer_token(authorization)

    # First attempt: local JWT verification using Supabase JWKS.
    try:
        return _decode_token_with_jwks(token)
    except Exception:
        # Fallback: remote validation via Supabase user endpoint.
        return await _fetch_user_from_supabase(token)
