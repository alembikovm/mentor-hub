"""Clerk session-token verification.

The web app sends `Authorization: Bearer <Clerk session JWT>`. We verify it
against the instance JWKS (networkless after the first key fetch).
"""

from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    url = get_settings().clerk_jwks_url
    if not url:
        raise RuntimeError("CLERK_JWKS_URL is not configured")
    return jwt.PyJWKClient(url, cache_keys=True)


def verify_clerk_token(token: str) -> dict:
    settings = get_settings()
    if not settings.clerk_jwks_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Auth is not configured: set CLERK_JWKS_URL"
        )
    try:
        key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer or None,
            options={"verify_iss": bool(settings.clerk_issuer), "verify_aud": False},
            leeway=5,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    azp = claims.get("azp")
    if azp and settings.authorized_parties and azp not in settings.authorized_parties:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized party")
    return claims


async def current_user_id(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return verify_clerk_token(creds.credentials)["sub"]


async def current_user(
    user_id: Annotated[str, Depends(current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        session.add(user)
        await session.commit()
    return user


def require_role(role: Role):
    async def dep(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role != role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Only {role}s can do this")
        return user

    return dep


CurrentUser = Annotated[User, Depends(current_user)]
Mentor = Annotated[User, Depends(require_role(Role.mentor))]
Mentee = Annotated[User, Depends(require_role(Role.mentee))]
DB = Annotated[AsyncSession, Depends(get_session)]
