import jwt
from fastapi import Depends, HTTPException, Request
from core.db import db
from core.permissions import allowed_modules
from core.security import decode_token
from core.sessions import session_active

PUBLIC_USER = {"_id": 0, "password_hash": 0}
DEACTIVATED = "Your account has been deactivated"
PASSWORD_CHANGE_PATHS = {"/api/auth/me", "/api/auth/logout", "/api/auth/set-password"}


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token
    header = request.headers.get("Authorization", "")
    return header[7:] if header.startswith("Bearer ") else None


async def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id, sid = decode_token(token, "access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not await session_active(sid, user_id):
        raise HTTPException(status_code=401, detail="Session has ended. Please sign in again.")
    user = await db.users.find_one({"id": user_id}, PUBLIC_USER)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("status") == "deactivated":
        raise HTTPException(status_code=401, detail=DEACTIVATED)
    if user.get("must_change_password") and request.url.path not in PASSWORD_CHANGE_PATHS:
        raise HTTPException(status_code=403, detail="Password change required")
    return user


def forbidden(message: str = "You don't have access to this resource") -> HTTPException:
    return HTTPException(status_code=403, detail=message)


def require_module(module: str):
    async def dep(user: dict = Depends(get_current_user)) -> dict:
        if module not in allowed_modules(user["role"]):
            raise forbidden()
        return user
    return dep


def require_org(*roles: str):
    async def dep(user: dict = Depends(get_current_user)) -> dict:
        if user["mode"] != "organisation" or not user.get("org_id"):
            raise forbidden("Organisation endpoints are not available for Individual accounts")
        if roles and user["role"] not in roles:
            raise forbidden()
        return user
    return dep
