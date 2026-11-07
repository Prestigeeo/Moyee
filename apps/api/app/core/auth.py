"""Supabase JWT verification.

Supports both Supabase signing modes:
- asymmetric signing keys (RS256/ES256) verified via the project's JWKS endpoint
- legacy shared secret (HS256) via SUPABASE_JWT_SECRET
"""

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_jwks_client: jwt.PyJWKClient | None = None


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode(token: str, settings: Settings) -> dict:
    global _jwks_client
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise _unauthorized("HS256 tokens are not accepted")
        key: object = settings.supabase_jwt_secret
    elif alg in ("RS256", "ES256"):
        if not settings.supabase_url:
            raise _unauthorized("Auth is not configured")
        if _jwks_client is None:
            _jwks_client = jwt.PyJWKClient(settings.jwks_url, cache_keys=True)
        key = _jwks_client.get_signing_key_from_jwt(token).key
    else:
        raise _unauthorized("Unsupported token algorithm")

    return jwt.decode(
        token,
        key,  # type: ignore[arg-type]
        algorithms=[alg],
        audience=settings.supabase_jwt_audience,
    )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if (
        settings.env == "local"
        and not settings.supabase_url
        and not settings.supabase_jwt_secret
        and (creds is None or creds.credentials == "local-dev-token")
    ):
        return CurrentUser(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="researcher@moyee.local",
        )
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        claims = _decode(creds.credentials, settings)
        return CurrentUser(id=uuid.UUID(claims["sub"]), email=claims.get("email"))
    except HTTPException:
        raise
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token") from None
