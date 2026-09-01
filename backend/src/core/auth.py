"""Auth dependencies: turn a request into the signed-in :class:`AdminUser`.

Two places a credential can live, checked in this order:

1. ``Authorization: Bearer <token>`` — what the admin console sends. It has to
   be a header rather than a cookie because the console can be pointed at a
   backend on another origin (``/admin/?api=https://…``), and this app's CORS is
   ``allow_origins=["*"]``, which browsers refuse to combine with credentialed
   (cookie-bearing) requests.
2. The ``cs_admin_token`` cookie — set at login so the static-file middleware in
   ``main.py`` can gate the HTML page itself, and so a plain browser visit works.

Both carry the identical token string; there is no second code path.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import AdminUser
from ..services import auth_service
from .config import get_settings
from .database import get_db
from .exceptions import AuthError
from .security import TokenError, decode_token, password_version


def extract_token(request: Request) -> Optional[str]:
    """Pull the raw token out of the Authorization header or the cookie."""
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
        if token:
            return token
    cookie = request.cookies.get(get_settings().auth.cookie_name)
    return cookie.strip() if cookie else None


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Optional[AdminUser]:
    """Resolve the signed-in admin, or raise :class:`AuthError` (401).

    Returns ``None`` — not a user — when ``AUTH_ENABLED=false``. Endpoints that
    actually need the user object all sit behind login anyway, and the ones that
    merely need "somebody is allowed in" don't look at the return value.
    """
    settings = get_settings()
    if not settings.auth.enabled:
        return None

    token = extract_token(request)
    if not token:
        raise AuthError("未登录或登录已过期，请重新登录")

    try:
        payload = decode_token(token, settings.app.secret_key)
    except TokenError as e:
        raise AuthError("未登录或登录已过期，请重新登录") from e

    uid = payload.get("uid")
    if not isinstance(uid, int):
        raise AuthError("未登录或登录已过期，请重新登录")

    user = await auth_service.get_by_id(db, uid)
    if user is None or not user.is_active:
        raise AuthError("账号不存在或已被停用")

    # The password fingerprint is checked here, not in decode_token, because
    # only now do we have the row: a token minted before a password change no
    # longer matches, so changing the password signs out every other device.
    if payload.get("pv") != password_version(user.password_hash):
        raise AuthError("密码已修改，请重新登录")

    return user


async def require_admin(user: Optional[AdminUser] = Depends(get_current_user)) -> Optional[AdminUser]:
    """Router-level guard. Used as ``dependencies=[Depends(require_admin)]``."""
    return user


async def current_user_or_401(
    request: Request, db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """For endpoints that need the actual row (``/api/auth/me`` and friends).

    Resolves against the *request's own* session so the caller can mutate and
    commit the returned row. With ``AUTH_ENABLED=false`` there is no signed-in
    user, so this falls back to the seed account — otherwise profile editing
    would break in demo mode.
    """
    user = await get_current_user(request, db)
    if user is not None:
        return user

    settings = get_settings()
    fallback = await auth_service.get_by_username(db, settings.auth.default_username)
    if fallback is None:
        raise AuthError("系统中没有可用账号")
    return fallback
