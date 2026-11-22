import hashlib
from fastapi import HTTPException, UploadFile
from pymongo import ReturnDocument
from datetime import timedelta
from core.db import db, new_id, now_iso, now_utc
from services.actions import conflict, history, notify
from services.lending import is_friend
from services.storage import put_object, get_object, APP_NAME
from services.users import audit
from services.validation import field_error

PRIORITIES = ("low", "medium", "high", "urgent")
TEXT_FIELDS = ("title", "description", "objective", "completed_work", "pending_work", "context_notes")
# Content only the sender and recipient may read. Admins/managers overseeing a handover see metadata only.
PRIVATE_FIELDS = ("description", "objective", "completed_work", "pending_work", "context_notes",
                  "rejection_reason", "completion_note")
RESTRICTED_NOTE = "Content is visible to the sender and recipient only."
DUPLICATE = "You already sent this handover to this person a moment ago"
CANT_ASSIGN = "You can't hand over to this user"
BAD_FILE = "Unsupported file or file too large (max 10 MB)"
ALLOWED_EXT = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
               "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               "txt": "text/plain", "md": "text/markdown"}
MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 5
P = {"_id": 0}


def norm(doc: dict) -> dict:
    """Reads both the Phase 3 shape and the Phase 1 seed shape (from_user_id/to_user_id, in_progress)."""
    status = "accepted" if doc.get("status") == "in_progress" else doc.get("status")
    return {**doc, "creator_id": doc.get("creator_id") or doc.get("from_user_id"),
            "assignee_id": doc.get("assignee_id") or doc.get("to_user_id"), "status": status,
            "priority": doc.get("priority", "medium"), "history": doc.get("history", [])}


async def _depts(*user_ids) -> set:
    return {u.get("department_id") async for u in db.users.find({"id": {"$in": list(user_ids)}}, {"_id": 0, "department_id": 1})} - {None}


async def can_view(user: dict, t: dict) -> bool:
    if user["id"] in (t["creator_id"], t["assignee_id"]):
        return True
    if user["mode"] != "organisation" or t.get("org_id") != user.get("org_id"):
        return False
    if user["role"] == "admin":
        return True
    return user["role"] == "manager" and user["department_id"] in await _depts(t["creator_id"], t["assignee_id"])


async def get_task(user: dict, task_id: str) -> dict:
    doc = await db.handovers.find_one({"id": task_id}, P)
    if not doc:
        raise HTTPException(status_code=404, detail="Handover not found")
    t = norm(doc)
    if not await can_view(user, t):
        raise HTTPException(status_code=403, detail="You don't have access to this handover")
    return t


async def _names(ids) -> dict:
    return {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1})}


def is_party(user: dict, t: dict) -> bool:
    return user["id"] in (t["creator_id"], t["assignee_id"])


async def serialize(user: dict, t: dict, detail: bool = False) -> dict:
    ids = {t["creator_id"], t["assignee_id"]} | {h["actor_id"] for h in t["history"]}
    names = await _names(ids)
    me_assignee, me_creator = user["id"] == t["assignee_id"], user["id"] == t["creator_id"]
    party = me_assignee or me_creator
    if not party:
        t = {k: v for k, v in t.items() if k not in PRIVATE_FIELDS}
        t["history"] = [{k: v for k, v in h.items() if k != "note"} for h in t["history"]]
    out = {**t, "creator_name": names.get(t["creator_id"]), "assignee_name": names.get(t["assignee_id"]),
           "attachment_count": await db.attachments.count_documents({"task_id": t["id"], "is_deleted": False}),
           "actions": {"accept": me_assignee and t["status"] == "pending", "reject": me_assignee and t["status"] == "pending",
                       "complete": me_assignee and t["status"] == "accepted", "cancel": me_creator and t["status"] == "pending",
                       "edit": me_creator and t["status"] == "pending",
                       "attach": me_creator and t["status"] in ("pending", "accepted")}}
    out.pop("from_user_id", None)
    out.pop("to_user_id", None)
    out["content_restricted"] = not party
    if not party:
        out["restricted_note"] = RESTRICTED_NOTE
    if detail:
        out["history"] = [{**h, "actor_name": names.get(h["actor_id"])} for h in t["history"]]
        out["attachments"] = (await db.attachments.find({"task_id": t["id"], "is_deleted": False},
                                                        {"_id": 0, "storage_path": 0}).sort("created_at", 1).to_list(MAX_FILES)) if party else []
    return out


async def list_tasks(user: dict, box: str, status: str | None) -> list[dict]:
    uid = user["id"]
    if box == "received":
        q = {"$or": [{"assignee_id": uid}, {"to_user_id": uid}]}
    elif box == "sent":
        q = {"$or": [{"creator_id": uid}, {"from_user_id": uid}]}
    else:
        if user["mode"] != "organisation" or user["role"] not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Only Managers and Admins can see all handovers")
        q = {"org_id": user["org_id"]}
    docs = await db.handovers.find(q, P).sort("created_at", -1).to_list(500)
    tasks = [norm(d) for d in docs]
    if box == "all" and user["role"] == "manager":
        tasks = [t for t in tasks if await can_view(user, t)]
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return [await serialize(user, t) for t in tasks]


async def assignees(user: dict) -> list[dict]:
    if user["mode"] == "individual":
        ids = []
        async for f in db.friendships.find({"status": "accepted", "$or": [{"requester_id": user["id"]}, {"addressee_id": user["id"]}]}, P):
            ids.append(f["addressee_id"] if f["requester_id"] == user["id"] else f["requester_id"])
        q = {"id": {"$in": ids}, "mode": "individual"}
    else:
        q = {"org_id": user["org_id"], "id": {"$ne": user["id"]}}
    depts = {d["id"]: d["name"] async for d in db.departments.find({}, {"_id": 0, "id": 1, "name": 1})}
    users = await db.users.find(q, {"_id": 0, "id": 1, "name": 1, "title": 1, "department_id": 1}).sort("name", 1).to_list(1000)
    return [{**u, "department": depts.get(u.get("department_id"))} for u in users]


async def _check_assignee(user: dict, assignee_id: str) -> None:
    target = await db.users.find_one({"id": assignee_id}, {"_id": 0, "id": 1, "mode": 1, "org_id": 1})
    ok = bool(target) and assignee_id != user["id"] and target["mode"] == user["mode"]
    if ok and user["mode"] == "individual":
        ok = await is_friend(user["id"], assignee_id)
    if ok and user["mode"] == "organisation":
        ok = target.get("org_id") == user["org_id"]
    if not ok:
        raise field_error(400, {"assignee_id": CANT_ASSIGN})


def _clean(body: dict) -> dict:
    data = {k: (body.get(k) or "").strip() for k in TEXT_FIELDS}
    errors = {}
    if not data["title"]:
        errors["title"] = "Add a title"
    if not data["pending_work"]:
        errors["pending_work"] = "Describe the pending work"
    priority = body.get("priority") or "medium"
    if priority not in PRIORITIES:
        errors["priority"] = "Choose low, medium, high or urgent"
    if errors:
        raise field_error(422, errors)
    return {**data, "priority": priority}


async def create(user: dict, body: dict) -> dict:
    data = _clean(body)
    assignee_id = (body.get("assignee_id") or "").strip()
    if not assignee_id:
        raise field_error(422, {"assignee_id": "Choose who to hand over to"})
    await _check_assignee(user, assignee_id)
    recent = (now_utc() - timedelta(minutes=2)).isoformat()
    if await db.handovers.find_one({"creator_id": user["id"], "assignee_id": assignee_id, "title": data["title"],
                                    "status": "pending", "created_at": {"$gte": recent}}, {"_id": 1}):
        raise conflict(DUPLICATE)
    now = now_iso()
    doc = {"id": new_id("hnd"), **data, "creator_id": user["id"], "assignee_id": assignee_id, "org_id": user.get("org_id"),
           "status": "pending", "created_at": now, "updated_at": now, "history": [history(user["id"], "created")]}
    await db.handovers.insert_one(doc)
    await notify(assignee_id, "handover.received", f"{user['name']} handed over “{data['title']}”", {"task_id": doc["id"]})
    await audit(user["id"], "handover.created", {"task_id": doc["id"], "assignee_id": assignee_id})
    return await serialize(user, norm(await db.handovers.find_one({"id": doc["id"]}, P)), True)


async def edit(user: dict, task_id: str, body: dict) -> dict:
    t = await get_task(user, task_id)
    if t["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator can edit this handover")
    data = _clean({**{k: t.get(k) for k in TEXT_FIELDS}, "priority": t["priority"], **body})
    done = await db.handovers.find_one_and_update({"id": task_id, "status": "pending"},
                                                  {"$set": {**data, "updated_at": now_iso()}, "$push": {"history": history(user["id"], "edited")}})
    if not done:
        raise conflict("Only pending handovers can be edited")
    await notify(t["assignee_id"], "handover.edited", f"{user['name']} updated “{data['title']}”", {"task_id": task_id})
    await audit(user["id"], "handover.edited", {"task_id": task_id})
    return await serialize(user, await get_task(user, task_id), True)


RULES = {"accept": ("assignee", ["pending"], "accepted"), "reject": ("assignee", ["pending"], "rejected"),
         "complete": ("assignee", ["accepted", "in_progress"], "completed"), "cancel": ("creator", ["pending"], "cancelled")}


async def transition(user: dict, task_id: str, action: str, note: str = "") -> dict:
    t = await get_task(user, task_id)
    actor, expect, new_status = RULES[action]
    if user["id"] != t[f"{actor}_id"]:
        raise HTTPException(status_code=403, detail=f"Only the {actor} can {action} this handover")
    if action == "reject" and not note.strip():
        raise field_error(422, {"reason": "Add a reason for rejecting"})
    extra = {"rejection_reason": note.strip()} if action == "reject" else {"completion_note": note.strip()} if action == "complete" else {}
    entry = history(user["id"], new_status, **({"note": note.strip()} if note.strip() else {}))
    done = await db.handovers.find_one_and_update({"id": task_id, "status": {"$in": expect}},
                                                  {"$set": {"status": new_status, "updated_at": now_iso(), **extra}, "$push": {"history": entry}},
                                                  return_document=ReturnDocument.AFTER)
    if not done:
        raise conflict(f"This handover is {t['status']}, so it can't be {new_status}")
    other = t["creator_id"] if actor == "assignee" else t["assignee_id"]
    await notify(other, f"handover.{new_status}", f"{user['name']} {new_status} “{t['title']}”", {"task_id": task_id})
    await audit(user["id"], f"handover.{new_status}", {"task_id": task_id, **extra})
    return await serialize(user, norm({k: v for k, v in done.items() if k != "_id"}), True)


async def add_attachment(user: dict, task_id: str, file: UploadFile) -> dict:
    t = await get_task(user, task_id)
    if t["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator can add attachments")
    if t["status"] not in ("pending", "accepted"):
        raise conflict("Attachments can't be added to a closed handover")
    if await db.attachments.count_documents({"task_id": task_id, "is_deleted": False}) >= MAX_FILES:
        raise HTTPException(status_code=400, detail=f"A handover can have at most {MAX_FILES} attachments")
    name = file.filename or "file"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    data = await file.read(MAX_BYTES + 1)
    if ext not in ALLOWED_EXT or len(data) > MAX_BYTES or not data:
        raise HTTPException(status_code=400, detail=BAD_FILE)
    aid = new_id("att")
    stored = await put_object(f"{APP_NAME}/handovers/{task_id}/{aid}.{ext}", data, ALLOWED_EXT[ext])
    doc = {"id": aid, "task_id": task_id, "storage_path": stored["path"], "filename": name, "content_type": ALLOWED_EXT[ext],
           "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "uploaded_by": user["id"], "is_deleted": False,
           "created_at": now_iso()}
    await db.attachments.insert_one(doc)
    await db.handovers.update_one({"id": task_id}, {"$push": {"history": history(user["id"], "attachment_added", note=name)}})
    await audit(user["id"], "handover.attachment_added", {"task_id": task_id, "attachment_id": aid, "size": len(data)})
    await notify(t["assignee_id"], "handover.attachment", f"{user['name']} attached {name} to “{t['title']}”", {"task_id": task_id})
    return {k: v for k, v in doc.items() if k not in ("_id", "storage_path")}


async def download(user: dict, task_id: str, attachment_id: str) -> tuple[bytes, dict]:
    t = await get_task(user, task_id)
    if not is_party(user, t):
        raise HTTPException(status_code=403, detail=RESTRICTED_NOTE)
    att = await db.attachments.find_one({"id": attachment_id, "task_id": task_id, "is_deleted": False}, P)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return await get_object(att["storage_path"]), att
