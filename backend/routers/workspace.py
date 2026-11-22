from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.db import db, now_iso
from core.deps import get_current_user, require_module, require_org, forbidden
from core.security import hash_password, verify_password
from services.reports import usage_report, allocation_report, lending_report, to_csv
from services.usage import check_days, load_providers
from services.users import audit
from services.validation import field_error

router = APIRouter(tags=["workspace"])
P = {"_id": 0}
CATEGORIES = ("lending", "allocation", "handover", "sessions")


# ---------- Notifications ----------
def _link(n: dict) -> Optional[str]:
    t, m = n["type"], n.get("meta") or {}
    if t.startswith(("lending", "friend")):
        return "/lending" + (f"?open={m['entry_id']}" if m.get("entry_id") else "")
    if t.startswith(("allocation", "resource_request")):
        return "/allocation"
    if t.startswith("handover"):
        return "/handover" + (f"?open={m['task_id']}" if m.get("task_id") else "")
    if t.startswith(("session", "planner")):
        return "/planner"
    return None


def _ntf(n: dict) -> dict:
    return {**n, "link": _link(n)}


async def _owned(user: dict, notification_id: str) -> dict:
    n = await db.notifications.find_one({"id": notification_id}, P)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n["user_id"] != user["id"]:
        raise forbidden("This notification belongs to someone else")
    return n


@router.get("/notifications", tags=["notifications"])
async def list_notifications(status: str = Query("all"), limit: int = Query(100, ge=1, le=200),
                             user: dict = Depends(get_current_user)):
    q = {"user_id": user["id"], **({"read": False} if status == "unread" else {})}
    items = await db.notifications.find(q, P).sort("created_at", -1).to_list(limit)
    return {"items": [_ntf(n) for n in items], "unread": await db.notifications.count_documents({"user_id": user["id"], "read": False})}


@router.get("/notifications/unread-count", tags=["notifications"])
async def unread_count(user: dict = Depends(get_current_user)):
    return {"unread": await db.notifications.count_documents({"user_id": user["id"], "read": False})}


@router.get("/notifications/pending", tags=["notifications"])
async def pending_actions(user: dict = Depends(get_current_user)):
    uid = user["id"]
    items = []

    async def add(key: str, label: str, link: str, coll: str, q: dict):
        if (n := await db[coll].count_documents(q)):
            items.append({"key": key, "label": label, "count": n, "link": link})

    if user["mode"] == "individual":
        await add("lending_to_accept", "Lending entries to accept or decline", "/lending", "lending_ledger",
                  {"status": "pending", "initiator_id": {"$ne": uid}, "$or": [{"lender_id": uid}, {"borrower_id": uid}]})
        await add("repayments_to_confirm", "Repayments to confirm", "/lending", "lending_repayments",
                  {"lender_id": uid, "status": "awaiting_confirmation"})
        await add("friend_requests", "Friend requests", "/lending", "friendships", {"addressee_id": uid, "status": "pending"})
    if user["role"] in ("admin", "manager"):
        scope = {"org_id": user["org_id"]} if user["role"] == "admin" else {"department_id": user["department_id"]}
        await add("requests_to_approve", "Resource requests to review", "/allocation", "resource_requests", {**scope, "status": "pending"})
    await add("handovers_to_accept", "Handovers to accept", "/handover", "handovers",
              {"status": "pending", "$or": [{"assignee_id": uid}, {"to_user_id": uid}]})
    await add("time_suggestions", "Suggested session times", "/planner", "sessions", {"user_id": uid, "suggestion.status": "pending"})
    return {"items": items, "total": sum(i["count"] for i in items)}


@router.get("/notifications/{notification_id}", tags=["notifications"])
async def get_notification(notification_id: str, user: dict = Depends(get_current_user)):
    return _ntf(await _owned(user, notification_id))


@router.post("/notifications/read-all", tags=["notifications"])
async def read_all(user: dict = Depends(get_current_user)):
    r = await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"updated": r.modified_count, "unread": 0}


@router.post("/notifications/{notification_id}/read", tags=["notifications"])
async def read_one(notification_id: str, user: dict = Depends(get_current_user)):
    await _owned(user, notification_id)
    await db.notifications.update_one({"id": notification_id}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"unread": await db.notifications.count_documents({"user_id": user["id"], "read": False})}


# ---------- Reports ----------
async def _report(user: dict, kind: str, days: int) -> dict:
    check_days(days)
    if kind == "usage":
        return await usage_report(user, days)
    if kind == "allocation" and user["role"] in ("admin", "manager"):
        return await allocation_report(user, days)
    if kind == "lending" and user["role"] == "individual":
        return await lending_report(user, days)
    raise forbidden("This report is not available for your role")


@router.get("/reports/{kind}", tags=["reports"])
async def report(kind: str, days: int = Query(30), user: dict = Depends(require_module("reports"))):
    return await _report(user, kind, days)


@router.get("/reports/{kind}/csv", tags=["reports"])
async def report_csv(kind: str, days: int = Query(30), user: dict = Depends(require_module("reports"))):
    data = to_csv(await _report(user, kind, days))
    name = f"{kind}-report-{days}d.csv"
    return StreamingResponse(iter([data]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------- Integrations ----------
def _integration_scope(user: dict) -> dict:
    return {"scope_type": "org", "scope_id": user["org_id"]} if user["role"] == "admin" else {"scope_type": "user", "scope_id": user["id"]}


@router.get("/integrations", tags=["integrations"])
async def integrations(user: dict = Depends(require_module("integrations"))):
    scope = _integration_scope(user)
    states = {s["provider_id"]: s["enabled"] async for s in db.integration_states.find(scope, P)}
    out = []
    for p in await load_providers():
        on = bool(states.get(p["id"]))
        out.append({"id": p["id"], "name": p["name"], "vendor": p["vendor"], "color": p["color"], "connected": False,
                    "simulated_connection": on, "status": "Simulated connection active" if on else "Simulated, not connected"})
    return {"scope": scope["scope_type"], "note": "No real provider data is retrieved.", "providers": out}


class ToggleIn(BaseModel):
    enabled: bool


@router.put("/integrations/{provider_id}", tags=["integrations"])
async def toggle_integration(provider_id: str, body: ToggleIn, user: dict = Depends(require_module("integrations"))):
    if provider_id not in {p["id"] for p in await load_providers()}:
        raise HTTPException(status_code=404, detail="Unknown provider")
    scope = _integration_scope(user)
    await db.integration_states.update_one({**scope, "provider_id": provider_id},
                                           {"$set": {"enabled": body.enabled, "updated_by": user["id"], "updated_at": now_iso()}}, upsert=True)
    await audit(user["id"], "integration.toggled", {"provider_id": provider_id, "enabled": body.enabled, **scope})
    return {"provider_id": provider_id, "simulated_connection": body.enabled,
            "status": "Simulated connection active" if body.enabled else "Simulated, not connected"}


# ---------- Settings ----------
def _prefs(doc: dict) -> dict:
    stored = doc.get("notification_prefs") or {}
    return {c: stored.get(c, True) for c in CATEGORIES}


@router.get("/settings", tags=["settings"])
async def get_settings(user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 1, "notification_prefs": 1})
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0, "id": 1, "name": 1}) if user.get("org_id") else None
    return {"profile": {"name": user["name"], "title": user.get("title"), "email": user["email"]},
            "auth_provider": user["auth_provider"], "is_demo": bool(user.get("is_demo")), "has_password": bool(doc.get("password_hash")),
            "notification_prefs": _prefs(doc), "organization": org if user["role"] == "admin" else None}


class ProfileIn(BaseModel):
    name: str = ""
    title: Optional[str] = None


@router.patch("/settings/profile", tags=["settings"])
async def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    name, title = body.name.strip(), (body.title or "").strip()
    errors = {}
    if not name:
        errors["name"] = "Enter your name"
    elif len(name) > 80:
        errors["name"] = "Name must be 80 characters or fewer"
    if len(title) > 80:
        errors["title"] = "Title must be 80 characters or fewer"
    if errors:
        raise field_error(422, errors)
    await db.users.update_one({"id": user["id"]}, {"$set": {"name": name, "title": title or None}})
    await audit(user["id"], "settings.profile_updated", {})
    return {"name": name, "title": title or None}


class PasswordIn(BaseModel):
    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""


@router.post("/settings/password", tags=["settings"])
async def change_password(body: PasswordIn, user: dict = Depends(get_current_user)):
    if user.get("is_demo"):
        raise forbidden("Password changes are disabled for demo accounts")
    doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 1})
    if not doc.get("password_hash"):
        raise HTTPException(status_code=400, detail="Signed in with Google. There is no password to change.")
    errors = {}
    if not verify_password(body.current_password, doc["password_hash"]):
        errors["current_password"] = "Current password is incorrect"
    if len(body.new_password) < 8:
        errors["new_password"] = "New password must be at least 8 characters"
    elif body.new_password != body.confirm_password:
        errors["confirm_password"] = "Passwords don't match"
    if errors:
        raise field_error(422, errors)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new_password), "password_changed_at": now_iso()}})
    await audit(user["id"], "auth.password_changed", {})
    return {"ok": True}


class PrefsIn(BaseModel):
    lending: bool = True
    allocation: bool = True
    handover: bool = True
    sessions: bool = True


@router.put("/settings/notifications", tags=["settings"])
async def update_prefs(body: PrefsIn, user: dict = Depends(get_current_user)):
    prefs = body.model_dump()
    await db.users.update_one({"id": user["id"]}, {"$set": {"notification_prefs": prefs}})
    await audit(user["id"], "settings.notifications_updated", prefs)
    return prefs


class OrgIn(BaseModel):
    name: str = ""


@router.patch("/org", tags=["organisation"])
async def rename_org(body: OrgIn, user: dict = Depends(require_org("admin"))):
    name = body.name.strip()
    if not name or len(name) > 80:
        raise field_error(422, {"name": "Enter an organisation name (up to 80 characters)"})
    await db.organizations.update_one({"id": user["org_id"]}, {"$set": {"name": name}})
    await audit(user["id"], "org.renamed", {"name": name})
    return {"id": user["org_id"], "name": name}
