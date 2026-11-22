import secrets
from datetime import timedelta
from fastapi import Response
from core.config import REFRESH_TTL_DAYS
from core.db import db, now_iso, now_utc
from core.security import set_auth_cookies


async def start_session(response: Response, user_id: str) -> str:
    sid = secrets.token_urlsafe(18)
    await db.auth_sessions.insert_one({"sid": sid, "user_id": user_id, "created_at": now_iso(),
                                       "expires_at": now_utc() + timedelta(days=REFRESH_TTL_DAYS)})
    return set_auth_cookies(response, user_id, sid)


async def session_active(sid: str | None, user_id: str) -> bool:
    return bool(sid) and bool(await db.auth_sessions.find_one({"sid": sid, "user_id": user_id, "revoked": {"$ne": True}}, {"_id": 1}))


async def revoke_session(sid: str) -> None:
    await db.auth_sessions.update_one({"sid": sid}, {"$set": {"revoked": True, "revoked_at": now_iso()}})


async def revoke_user_sessions(user_id: str) -> None:
    await db.auth_sessions.update_many({"user_id": user_id, "revoked": {"$ne": True}}, {"$set": {"revoked": True, "revoked_at": now_iso()}})
