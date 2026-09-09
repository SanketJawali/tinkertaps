from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, raise_api_error
from app.db.session import get_db
from app.models.users import User


@dataclass(slots=True)
class AuthContext:
    user: User
    is_anonymous: bool
    set_anon_cookie: bool = False
    anon_cookie_value: str | None = None


@lru_cache
def _get_jwks_client() -> PyJWKClient:
    if not settings.clerk_jwks_url:
        raise RuntimeError("CLERK_JWKS_URL is not configured")
    return PyJWKClient(settings.clerk_jwks_url)


def verify_clerk_token(token: str) -> dict:
    if not settings.clerk_issuer or not settings.clerk_jwks_url:
        raise_api_error(
            code=ErrorCode.AUTH_NOT_CONFIGURED,
            message="Clerk authentication is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "issuer": settings.clerk_issuer,
        }
        if settings.clerk_audience:
            decode_kwargs["audience"] = settings.clerk_audience
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        return jwt.decode(token, signing_key.key, **decode_kwargs)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        ) from exc


async def _get_or_create_clerk_user(
    db: AsyncSession,
    clerk_user_id: str,
) -> User:
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        clerk_user_id=clerk_user_id,
        anonymous_id=None,
        credits=settings.registered_default_credits,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _get_or_create_anonymous_user(
    db: AsyncSession,
    anonymous_id: uuid.UUID | None,
) -> tuple[User, bool, uuid.UUID]:
    """Return (user, needs_cookie_set, anonymous_id)."""
    if anonymous_id is not None:
        result = await db.execute(
            select(User).where(User.anonymous_id == anonymous_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user, False, anonymous_id

    new_anonymous_id = uuid.uuid4()
    user = User(
        clerk_user_id=None,
        anonymous_id=new_anonymous_id,
        credits=settings.anonymous_default_credits,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True, new_anonymous_id


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return token


async def get_auth_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    authorization = request.headers.get("Authorization")
    anon_cookie_value = request.cookies.get(settings.anon_cookie_name)
    return await resolve_auth_context(
        db=db,
        authorization=authorization,
        anon_cookie_value=anon_cookie_value,
    )


async def resolve_auth_context(
    *,
    db: AsyncSession,
    authorization: str | None,
    anon_cookie_value: str | None,
) -> AuthContext:
    token = _parse_bearer_token(authorization)
    if token is not None:
        claims = verify_clerk_token(token)
        clerk_user_id = claims.get("sub")
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
            )
        user = await _get_or_create_clerk_user(db, clerk_user_id)
        return AuthContext(user=user, is_anonymous=False)

    parsed_anon_id: uuid.UUID | None = None
    if anon_cookie_value:
        try:
            parsed_anon_id = uuid.UUID(anon_cookie_value)
        except ValueError:
            parsed_anon_id = None

    user, needs_cookie, anonymous_id = await _get_or_create_anonymous_user(
        db, parsed_anon_id
    )
    return AuthContext(
        user=user,
        is_anonymous=True,
        set_anon_cookie=needs_cookie,
        anon_cookie_value=str(anonymous_id),
    )


def apply_anon_cookie(response: Response, auth: AuthContext) -> None:
    if not auth.set_anon_cookie or not auth.anon_cookie_value:
        return
    response.set_cookie(
        key=settings.anon_cookie_name,
        value=auth.anon_cookie_value,
        max_age=settings.anon_cookie_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
