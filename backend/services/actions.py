from datetime import date
from typing import Any
from fastapi import HTTPException
from core.db import db, new_id, now_iso, today_utc
from services.validation import field_error


def parse_credits(value: Any, field: str = "amount", minimum: int = 1) -> int:
    n = None
    if isinstance(value, bool):
        n = None
    elif isinstance(value, int):
        n = value
    elif isinstance(value, float) and value.is_integer():
        n = int(value)
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        n = int(value.strip())
    if n is None or n < minimum:
        msg = "Enter a whole number of credits greater than 0" if minimum > 0 else "Enter a whole number of credits (0 or more)"
        raise field_error(422, {field: msg})
    return n


def parse_due_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        raise field_error(422, {"due_date": "Enter a valid date"})
    if d < today_utc():
        raise field_error(422, {"due_date": "Due date can't be in the past"})
    return d.isoformat()


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def conflict(message: str = "This item was already updated. Refresh to see its latest status.") -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def history(actor_id: str, action: str, **extra) -> dict:
    return {"at": now_iso(), "actor_id": actor_id, "action": action, **extra}


PREF_CATEGORY = {"lending": "lending", "friend": "lending", "allocation": "allocation", "resource_request": "allocation",
                 "handover": "handover", "session": "sessions", "planner": "sessions"}


async def notify(user_id: str, type_: str, title: str, meta: dict | None = None) -> None:
    cat = PREF_CATEGORY.get(type_.split(".")[0])
    if cat:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "notification_prefs": 1})
        if u and (u.get("notification_prefs") or {}).get(cat) is False:
            return
    await db.notifications.insert_one({"id": new_id("ntf"), "user_id": user_id, "type": type_, "title": title,
                                       "meta": meta or {}, "read": False, "created_at": now_iso()})
