import asyncio
import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from pymongo import ReturnDocument
from core.db import db, new_id, now_iso, now_utc
from services.actions import parse_credits, conflict, history, notify
from services.users import audit
from services.validation import field_error

DISCLAIMER = "Planning sessions does not create extra provider capacity or bypass usage limits."
OVERLAP = "Overlaps another session"
REMINDERS = (None, 15, 30, 60)
RESET_TYPES = ("daily", "weekly", "monthly", "rolling")
P = {"_id": 0}
log = logging.getLogger("planner")


def _dt(value) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat(timespec="seconds")


def norm(s: dict) -> dict:
    """Reads both Phase 3 sessions and the Phase 1 seed shape (date-only start_at, title)."""
    start = _dt(s["start_at"] if len(s["start_at"]) > 10 else f"{s['start_at']}T09:00:00+00:00")
    end = _dt(s.get("end_at")) or start + timedelta(minutes=s.get("duration_min", 60))
    return {**s, "start_at": _iso(start), "end_at": _iso(end), "purpose": s.get("purpose") or s.get("title", ""),
            "reminder_min": s.get("reminder_min"), "suggestion": s.get("suggestion"), "history": s.get("history", [])}


async def _providers() -> dict:
    return {p["id"]: p async for p in db.providers.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "color": 1})}


async def _validate(body: dict, providers: dict) -> dict:
    errors = {}
    if body.get("provider_id") not in providers:
        errors["provider_id"] = "Choose a provider"
    start, end = _dt(body.get("start_at")), _dt(body.get("end_at"))
    if not start:
        errors["start_at"] = "Enter a valid start date and time"
    elif start < now_utc():
        errors["start_at"] = "Start time can't be in the past"
    if not end:
        errors["end_at"] = "Enter a valid end time"
    elif start and end <= start:
        errors["end_at"] = "End time must be after the start time"
    try:
        credits = parse_credits(body.get("estimated_credits"), "estimated_credits")
    except HTTPException:
        errors["estimated_credits"] = "Estimated credits must be greater than 0"
    if not (body.get("purpose") or "").strip():
        errors["purpose"] = "Add a purpose"
    reminder = body.get("reminder_min")
    if reminder not in REMINDERS:
        errors["reminder_min"] = "Choose 15, 30 or 60 minutes"
    if errors:
        raise field_error(422, errors)
    return {"provider_id": body["provider_id"], "start_at": _iso(start), "end_at": _iso(end),
            "duration_min": int((end - start).total_seconds() // 60), "estimated_credits": credits,
            "purpose": body["purpose"].strip(), "reminder_min": reminder,
            "remind_at": _iso(start - timedelta(minutes=reminder)) if reminder else None, "reminder_sent": False}


async def _own_sessions(user_id: str) -> list[dict]:
    return [norm(s) for s in await db.sessions.find({"user_id": user_id}, P).to_list(2000)]


def _overlaps(s: dict, others: list[dict]) -> bool:
    return any(o["id"] != s["id"] and o["status"] == "planned" and o["start_at"] < s["end_at"] and s["start_at"] < o["end_at"]
               for o in others)


async def _serialize(sessions: list[dict], viewer_id: str) -> list[dict]:
    providers = await _providers()
    names = {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": list({s["user_id"] for s in sessions})}}, {"_id": 0, "id": 1, "name": 1})}
    by_user: dict = {}
    for uid in {s["user_id"] for s in sessions}:
        by_user[uid] = await _own_sessions(uid)
    return [{**s, "provider_name": providers.get(s["provider_id"], {}).get("name"), "provider_color": providers.get(s["provider_id"], {}).get("color"),
             "user_name": names.get(s["user_id"]), "overlaps": s["status"] == "planned" and _overlaps(s, by_user[s["user_id"]]),
             "mine": s["user_id"] == viewer_id} for s in sorted(sessions, key=lambda x: x["start_at"])]


def _in_range(s: dict, start: str | None, end: str | None) -> bool:
    return (not start or s["end_at"] > start) and (not end or s["start_at"] < end)


async def list_mine(user: dict, start: str | None, end: str | None) -> dict:
    sessions = await _own_sessions(user["id"])
    now = _iso(now_utc())
    upcoming = [s for s in sessions if s["status"] == "planned" and s["end_at"] > now]
    return {"sessions": await _serialize([s for s in sessions if _in_range(s, start, end)], user["id"]),
            "upcoming": (await _serialize(upcoming, user["id"]))[:20], "disclaimer": DISCLAIMER}


async def list_team(user: dict, start: str | None, end: str | None, member_id: str | None) -> dict:
    scope = {"org_id": user["org_id"], **({"department_id": user["department_id"]} if user["role"] == "manager" else {})}
    members = await db.users.find(scope, {"_id": 0, "id": 1, "name": 1, "department_id": 1}).sort("name", 1).to_list(1000)
    ids = [m["id"] for m in members]
    if member_id:
        if member_id not in ids:
            raise HTTPException(status_code=403, detail="That member is outside your scope")
        ids = [member_id]
    docs = [norm(s) for s in await db.sessions.find({"user_id": {"$in": ids}}, P).to_list(5000)]
    return {"sessions": await _serialize([s for s in docs if _in_range(s, start, end)], user["id"]), "members": members,
            "disclaimer": DISCLAIMER}


async def create(user: dict, body: dict) -> dict:
    data = await _validate(body, await _providers())
    doc = {"id": new_id("ses"), "user_id": user["id"], "org_id": user.get("org_id"), "department_id": user.get("department_id"),
           **data, "status": "planned", "suggestion": None, "created_at": now_iso(), "history": [history(user["id"], "created")]}
    await db.sessions.insert_one(doc)
    await audit(user["id"], "session.created", {"session_id": doc["id"], "start_at": data["start_at"]})
    await notify(user["id"], "session.created", f"Session planned: {data['purpose']}", {"session_id": doc["id"]})
    await process_reminders()
    s = (await _serialize([norm(await db.sessions.find_one({"id": doc["id"]}, P))], user["id"]))[0]
    return {"session": s, "warning": OVERLAP if s["overlaps"] else None}


async def _own(user: dict, session_id: str) -> dict:
    s = await db.sessions.find_one({"id": session_id}, P)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only change your own sessions")
    return norm(s)


async def update(user: dict, session_id: str, body: dict) -> dict:
    s = await _own(user, session_id)
    data = await _validate({k: s.get(k) for k in ("provider_id", "start_at", "end_at", "estimated_credits", "purpose", "reminder_min")} | body,
                           await _providers())
    done = await db.sessions.find_one_and_update({"id": session_id, "status": "planned"},
                                                 {"$set": {**data, "updated_at": now_iso()}, "$push": {"history": history(user["id"], "edited")}})
    if not done:
        raise conflict("Only planned sessions can be edited")
    await audit(user["id"], "session.edited", {"session_id": session_id})
    await notify(user["id"], "session.edited", f"Session updated: {data['purpose']}", {"session_id": session_id})
    await process_reminders()
    s = (await _serialize([norm(await db.sessions.find_one({"id": session_id}, P))], user["id"]))[0]
    return {"session": s, "warning": OVERLAP if s["overlaps"] else None}


async def set_status(user: dict, session_id: str, status: str) -> dict:
    s = await _own(user, session_id)
    done = await db.sessions.find_one_and_update({"id": session_id, "status": "planned"},
                                                 {"$set": {"status": status, "updated_at": now_iso()}, "$push": {"history": history(user["id"], status)}},
                                                 return_document=ReturnDocument.AFTER)
    if not done:
        raise conflict(f"This session is already {s['status']}")
    await audit(user["id"], f"session.{status}", {"session_id": session_id})
    await notify(user["id"], f"session.{status}", f"Session {status}: {s['purpose']}", {"session_id": session_id})
    return (await _serialize([norm({k: v for k, v in done.items() if k != "_id"})], user["id"]))[0]


async def suggest(user: dict, session_id: str, body: dict) -> dict:
    s = await db.sessions.find_one({"id": session_id}, P)
    if not s or s.get("org_id") != user["org_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    if user["role"] == "manager" and s.get("department_id") != user["department_id"]:
        raise HTTPException(status_code=403, detail="Managers can only suggest times for their own department")
    start, end = _dt(body.get("start_at")), _dt(body.get("end_at"))
    if not start or start < now_utc():
        raise field_error(422, {"start_at": "Start time can't be in the past"})
    if not end or end <= start:
        raise field_error(422, {"end_at": "End time must be after the start time"})
    sug = {"id": new_id("sug"), "by": user["id"], "by_name": user["name"], "start_at": _iso(start), "end_at": _iso(end),
           "note": (body.get("note") or "").strip(), "status": "pending", "created_at": now_iso()}
    done = await db.sessions.find_one_and_update({"id": session_id, "status": "planned"},
                                                 {"$set": {"suggestion": sug}, "$push": {"history": history(user["id"], "suggested", note=sug["note"])}})
    if not done:
        raise conflict("Only planned sessions can be rescheduled")
    purpose = norm(s)["purpose"]
    await notify(s["user_id"], "session.suggestion", f"{user['name']} suggested a new time for “{purpose}”", {"session_id": session_id})
    await audit(user["id"], "session.suggested", {"session_id": session_id, "start_at": sug["start_at"]})
    return (await _serialize([norm(await db.sessions.find_one({"id": session_id}, P))], user["id"]))[0]


async def respond_suggestion(user: dict, session_id: str, accept: bool) -> dict:
    s = await _own(user, session_id)
    sug = s.get("suggestion") or {}
    if sug.get("status") != "pending":
        raise conflict("There is no pending suggestion for this session")
    updates = {"suggestion.status": "accepted" if accept else "dismissed", "updated_at": now_iso()}
    if accept:
        start, end = _dt(sug["start_at"]), _dt(sug["end_at"])
        updates |= {"start_at": sug["start_at"], "end_at": sug["end_at"], "duration_min": int((end - start).total_seconds() // 60),
                    "reminder_sent": False,
                    "remind_at": _iso(start - timedelta(minutes=s["reminder_min"])) if s.get("reminder_min") else None}
    action = "suggestion_accepted" if accept else "suggestion_dismissed"
    done = await db.sessions.find_one_and_update({"id": session_id, "suggestion.status": "pending"},
                                                 {"$set": updates, "$push": {"history": history(user["id"], action)}})
    if not done:
        raise conflict("There is no pending suggestion for this session")
    await notify(sug["by"], f"session.{action}", f"{user['name']} {'accepted' if accept else 'dismissed'} your suggested time", {"session_id": session_id})
    await audit(user["id"], f"session.{action}", {"session_id": session_id})
    await process_reminders()
    return (await _serialize([norm(await db.sessions.find_one({"id": session_id}, P))], user["id"]))[0]


async def list_resets(user: dict) -> list[dict]:
    providers = await _providers()
    docs = await db.provider_resets.find({"user_id": user["id"]}, P).sort("next_reset_at", 1).to_list(50)
    return [{**d, "provider_name": providers.get(d["provider_id"], {}).get("name"), "label": "Entered by you"} for d in docs]


async def save_reset(user: dict, body: dict) -> list[dict]:
    errors = {}
    if body.get("provider_id") not in await _providers():
        errors["provider_id"] = "Choose a provider"
    if body.get("reset_type") not in RESET_TYPES:
        errors["reset_type"] = "Choose daily, weekly, monthly or rolling"
    hours = body.get("rolling_hours")
    if body.get("reset_type") == "rolling" and not (isinstance(hours, int) and 1 <= hours <= 168):
        errors["rolling_hours"] = "Enter 1–168 hours"
    nxt = _dt(body.get("next_reset_at"))
    if not nxt:
        errors["next_reset_at"] = "Enter the next reset time"
    if errors:
        raise field_error(422, errors)
    await db.provider_resets.update_one(
        {"user_id": user["id"], "provider_id": body["provider_id"]},
        {"$set": {"reset_type": body["reset_type"], "rolling_hours": hours if body["reset_type"] == "rolling" else None,
                  "next_reset_at": _iso(nxt), "source": "user", "updated_at": now_iso()},
         "$setOnInsert": {"id": new_id("rst"), "created_at": now_iso()}}, upsert=True)
    await audit(user["id"], "planner.reset_saved", {"provider_id": body["provider_id"]})
    await notify(user["id"], "planner.reset_saved", "Provider reset time saved", {"provider_id": body["provider_id"]})
    return await list_resets(user)


async def delete_reset(user: dict, reset_id: str) -> list[dict]:
    res = await db.provider_resets.delete_one({"id": reset_id, "user_id": user["id"]})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Reset time not found")
    await audit(user["id"], "planner.reset_deleted", {"reset_id": reset_id})
    return await list_resets(user)


async def process_reminders() -> int:
    now = _iso(now_utc())
    sent = 0
    async for s in db.sessions.find({"status": "planned", "reminder_sent": False, "remind_at": {"$ne": None, "$lte": now}}, P):
        claimed = await db.sessions.find_one_and_update({"id": s["id"], "reminder_sent": False}, {"$set": {"reminder_sent": True}})
        if not claimed or s["start_at"] < now:
            continue
        when = _dt(s["start_at"]).strftime("%b %d, %H:%M UTC")
        await notify(s["user_id"], "session.reminder", f"Upcoming session: {s['purpose']} at {when}", {"session_id": s["id"]})
        sent += 1
    return sent


async def reminder_loop() -> None:
    while True:
        try:
            await process_reminders()
        except Exception as exc:
            log.error("reminder loop: %s", exc)
        await asyncio.sleep(60)
