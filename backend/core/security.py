from datetime import timedelta
import bcrypt
import jwt
from fastapi import Response
from core.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TTL_MINUTES, REFRESH_TTL_DAYS, COOKIE_SECURE
from core.db import now_utc


SAMESITE = "none" if COOKIE_SECURE else "lax"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _token(user_id: str, kind: str, ttl: timedelta, sid: str) -> str:
    payload = {"sub": user_id, "type": kind, "sid": sid, "exp": now_utc() + ttl}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, sid: str) -> str:
    return _token(user_id, "access", timedelta(minutes=ACCESS_TTL_MINUTES), sid)


def create_refresh_token(user_id: str, sid: str) -> str:
    return _token(user_id, "refresh", timedelta(days=REFRESH_TTL_DAYS), sid)


def decode_token(token: str, kind: str) -> tuple[str, str | None]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != kind:
        raise jwt.InvalidTokenError("wrong token type")
    return payload["sub"], payload.get("sid")


def token_sid(token: str | None) -> str | None:
    """Session id from a token signed by us, even if expired (used on logout)."""
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False}).get("sid")
    except jwt.InvalidTokenError:
        return None


def _cookie(response: Response, key: str, value: str, max_age: int) -> None:
    response.set_cookie(key=key, value=value, httponly=True, secure=COOKIE_SECURE, samesite=SAMESITE, max_age=max_age, path="/")


def set_auth_cookies(response: Response, user_id: str, sid: str) -> str:
    access = create_access_token(user_id, sid)
    _cookie(response, "access_token", access, ACCESS_TTL_MINUTES * 60)
    _cookie(response, "refresh_token", create_refresh_token(user_id, sid), REFRESH_TTL_DAYS * 86400)
    return access


def set_access_cookie(response: Response, user_id: str, sid: str) -> str:
    access = create_access_token(user_id, sid)
    _cookie(response, "access_token", access, ACCESS_TTL_MINUTES * 60)
    return access


def clear_auth_cookies(response: Response) -> None:
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key, path="/", secure=COOKIE_SECURE, samesite=SAMESITE, httponly=True)
