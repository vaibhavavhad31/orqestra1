from datetime import timedelta
import httpx
import jwt
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from core.config import EMERGENT_SESSION_URL, ENABLE_EMERGENT_GOOGLE_AUTH
from core.db import db, now_utc, now_iso
from core.deps import get_current_user, DEACTIVATED
from core.security import hash_password, verify_password, set_access_cookie, clear_auth_cookies, decode_token, token_sid
from core.sessions import start_session, session_active, revoke_session
from core.deps import _extract_token
from models.schemas import RegisterIn, LoginIn, GoogleSessionIn, GoogleCompleteIn, UserOut, AuthOut
from services.users import serialize_user, create_account, audit, get_user
from services.validation import validate_signup, validate_mode, field_error

router = APIRouter(prefix="/auth", tags=["auth"])
MAX_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)


async def _issue(response: Response, user: dict) -> AuthOut:
    token = await start_session(response, user["id"])
    return AuthOut(user=await serialize_user(user), access_token=token)


def _identifier(request: Request, email: str) -> str:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    return f"{ip}:{email}"


@router.post("/register", response_model=AuthOut)
async def register(body: RegisterIn, response: Response):
    email = body.email.strip().lower()
    validate_signup(body.name, email, body.password, body.mode, body.org_name)
    if await db.users.find_one({"email": email}, {"_id": 1}):
        raise field_error(409, {"email": "An account with this email already exists"})
    user = await create_account(name=body.name.strip(), email=email, mode=body.mode,
                                org_name=body.org_name.strip(), auth_provider="password",
                                password_hash=hash_password(body.password))
    return await _issue(response, user)


@router.post("/login", response_model=AuthOut)
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ident = _identifier(request, email)
    attempt = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0})
    if attempt and attempt["count"] >= MAX_ATTEMPTS and attempt["last"] > (now_utc() - LOCKOUT).isoformat():
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last": now_iso()}}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    if user.get("status") == "deactivated":
        raise HTTPException(status_code=403, detail=DEACTIVATED)
    await audit(user["id"], "auth.login", {"method": "password"})
    user.pop("password_hash", None)
    return await _issue(response, user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    for token in {_extract_token(request), request.cookies.get("refresh_token")}:
        if sid := token_sid(token):
            await revoke_session(sid)
    clear_auth_cookies(response)
    return {"ok": True}


class SetPasswordIn(BaseModel):
    new_password: str = ""
    confirm_password: str = ""


@router.post("/set-password")
async def set_password(body: SetPasswordIn, user: dict = Depends(get_current_user)):
    if not user.get("must_change_password"):
        raise HTTPException(status_code=400, detail="No password change is required")
    if len(body.new_password) < 8:
        raise field_error(422, {"new_password": "New password must be at least 8 characters"})
    if body.new_password != body.confirm_password:
        raise field_error(422, {"confirm_password": "Passwords don't match"})
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new_password), "password_changed_at": now_iso()},
                                                   "$unset": {"must_change_password": ""}})
    await audit(user["id"], "auth.password_set", {})
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return await serialize_user(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        user_id, sid = decode_token(token, "refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not await session_active(sid, user_id):
        raise HTTPException(status_code=401, detail="Session has ended. Please sign in again.")
    if not await get_user(user_id):
        raise HTTPException(status_code=401, detail="User not found")
    if (await get_user(user_id)).get("status") == "deactivated":
        raise HTTPException(status_code=401, detail=DEACTIVATED)
    return {"access_token": set_access_cookie(response, user_id, sid)}


@router.post("/google/session")
async def google_session(body: GoogleSessionIn, response: Response):
    if not ENABLE_EMERGENT_GOOGLE_AUTH:
        raise HTTPException(status_code=503, detail="Google sign-in isn't available on this deployment. Use email or a demo login.")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
    data = r.json()
    if not data.get("email"):
        raise HTTPException(status_code=401, detail="Google sign-in did not return an email")
    email = data["email"].strip().lower()
    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if user:
        if user.get("is_demo"):
            raise HTTPException(status_code=403, detail="Demo accounts sign in with the one-click demo buttons")
        if user.get("status") == "deactivated":
            raise HTTPException(status_code=403, detail=DEACTIVATED)
        await db.users.update_one({"id": user["id"]}, {"$set": {"picture": data.get("picture"), "google_linked": True}})
        await audit(user["id"], "auth.login", {"method": "google"})
        return {"status": "authenticated", **(await _issue(response, user)).model_dump()}
    token = secrets.token_urlsafe(32)
    await db.pending_google_signups.insert_one({"token": token, "email": email, "name": data.get("name") or email,
                                                "picture": data.get("picture"),
                                                "expires_at": now_utc() + timedelta(minutes=30)})
    return {"status": "needs_mode", "pending_token": token, "email": email, "name": data.get("name")}


@router.post("/google/complete", response_model=AuthOut)
async def google_complete(body: GoogleCompleteIn, response: Response):
    errors: dict[str, str] = {}
    validate_mode(body.mode, body.org_name, errors)
    if errors:
        raise field_error(422, errors)
    pending = await db.pending_google_signups.find_one({"token": body.pending_token}, {"_id": 0})
    expires = pending["expires_at"] if pending else None
    if not pending or expires.replace(tzinfo=expires.tzinfo or now_utc().tzinfo) < now_utc():
        raise HTTPException(status_code=401, detail="Your Google sign-in expired. Please try again.")
    if await db.users.find_one({"email": pending["email"]}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = await create_account(name=pending["name"], email=pending["email"], mode=body.mode,
                                org_name=body.org_name.strip(), auth_provider="google", picture=pending.get("picture"))
    await db.pending_google_signups.delete_one({"token": body.pending_token})
    return await _issue(response, user)
