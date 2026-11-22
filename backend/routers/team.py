import re
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from core.db import db, new_id, now_iso
from core.deps import require_module, require_org
from core.security import hash_password
from core.sessions import revoke_user_sessions
from services.allocation import dept_allocated, ALLOC_EXCEEDS
from services.usage import allocation_map
from services.users import audit
from services.validation import field_error

router = APIRouter(tags=["team"])
admin_only = require_org("admin")
P = {"_id": 0, "password_hash": 0}
ROLES = ("admin", "manager", "employee")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _bad(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)


async def _depts(org_id: str) -> dict:
    return {d["id"]: d for d in await db.departments.find({"org_id": org_id}, {"_id": 0}).to_list(200)}


async def _serialize(users: list[dict], depts: dict) -> list[dict]:
    allocs = await allocation_map("user", [u["id"] for u in users])
    return [{"id": u["id"], "name": u["name"], "email": u["email"], "title": u.get("title"), "role": u["role"],
             "department_id": u.get("department_id"), "department": depts.get(u.get("department_id"), {}).get("name"),
             "status": u.get("status", "active"), "is_demo": bool(u.get("is_demo")),
             "monthly_allocation": allocs.get(u["id"], 0)} for u in users]


@router.get("/team/members")
async def team_members(q: Optional[str] = Query(None), department_id: Optional[str] = Query(None),
                       user: dict = Depends(require_module("team"))):
    query = {"org_id": user["org_id"]} if user["role"] == "admin" else {"department_id": user["department_id"]}
    if department_id and user["role"] == "admin":
        query["department_id"] = department_id
    if q and q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        query["$or"] = [{"name": rx}, {"email": rx}, {"title": rx}]
    users = await db.users.find(query, P).sort("name", 1).to_list(1000)
    depts = await _depts(user["org_id"])
    return {"members": await _serialize(users, depts), "can_manage": user["role"] == "admin",
            "departments": [{"id": d["id"], "name": d["name"]} for d in sorted(depts.values(), key=lambda d: d["name"])
                            if user["role"] == "admin" or d["id"] == user["department_id"]]}


class MemberIn(BaseModel):
    name: str = ""
    email: str = ""
    role: str = ""
    department_id: str = ""
    title: str = ""


@router.post("/team/members")
async def add_member(body: MemberIn, user: dict = Depends(admin_only)):
    name, email, title = body.name.strip(), body.email.strip().lower(), body.title.strip()
    depts = await _depts(user["org_id"])
    errors = {}
    if not name:
        errors["name"] = "Enter a name"
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address"
    if body.role not in ROLES:
        errors["role"] = "Choose a role"
    if body.department_id not in depts:
        errors["department_id"] = "Choose a department"
    if not title:
        errors["title"] = "Enter a job title"
    if not errors.get("email") and await db.users.find_one({"email": email}, {"_id": 1}):
        errors["email"] = "An account with this email already exists"
    if errors:
        raise field_error(422, errors)
    temp = secrets.token_urlsafe(9)
    uid, now = new_id("usr"), now_iso()
    await db.users.insert_one({"id": uid, "email": email, "name": name, "title": title, "mode": "organisation", "role": body.role,
                               "org_id": user["org_id"], "department_id": body.department_id, "is_demo": False,
                               "auth_provider": "password", "picture": None, "status": "active", "created_at": now,
                               "created_by": user["id"], "password_hash": hash_password(temp), "must_change_password": True})
    await db.allocations.insert_one({"id": new_id("alc"), "scope_type": "user", "scope_id": uid, "credits": 0,
                                     "period": "monthly", "created_at": now})
    await audit(user["id"], "team.member_added", {"user_id": uid, "role": body.role, "department_id": body.department_id})
    member = (await _serialize([await db.users.find_one({"id": uid}, P)], depts))[0]
    return {"member": member, "temporary_password": temp}


class MemberUpdateIn(BaseModel):
    role: Optional[str] = None
    department_id: Optional[str] = None
    title: Optional[str] = None


async def _target(user: dict, member_id: str) -> dict:
    t = await db.users.find_one({"id": member_id, "org_id": user["org_id"]}, P)
    if not t:
        raise HTTPException(status_code=404, detail="Member not found")
    return t


@router.patch("/team/members/{member_id}")
async def update_member(member_id: str, body: MemberUpdateIn, user: dict = Depends(admin_only)):
    t = await _target(user, member_id)
    depts = await _depts(user["org_id"])
    changes = {}
    if body.role is not None and body.role != t["role"]:
        if body.role not in ROLES:
            raise field_error(422, {"role": "Choose a role"})
        if t["id"] == user["id"]:
            raise _bad("You can't change your own role")
        if t.get("is_demo"):
            raise _bad("Demo accounts are protected. Their role can't be changed.")
        changes["role"] = body.role
    if body.department_id is not None and body.department_id != t.get("department_id"):
        if body.department_id not in depts:
            raise field_error(422, {"department_id": "Choose a department"})
        if t.get("is_demo"):
            raise _bad("Demo accounts are protected. Their department can't be changed.")
        mine = (await allocation_map("user", [t["id"]])).get(t["id"], 0)
        budget = (await allocation_map("department", [body.department_id])).get(body.department_id, 0)
        if mine and await dept_allocated(body.department_id) + mine > budget:
            raise _bad(ALLOC_EXCEEDS)
        changes["department_id"] = body.department_id
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise field_error(422, {"title": "Enter a job title"})
        changes["title"] = title
    if changes:
        await db.users.update_one({"id": t["id"]}, {"$set": changes})
        await audit(user["id"], "team.member_updated", {"user_id": t["id"], **changes})
    return (await _serialize([await db.users.find_one({"id": t["id"]}, P)], depts))[0]


async def _set_status(user: dict, member_id: str, status: str) -> dict:
    t = await _target(user, member_id)
    if status == "deactivated":
        if t["id"] == user["id"]:
            raise _bad("You can't deactivate your own account")
        if t.get("is_demo"):
            raise _bad("Demo accounts are protected and can't be deactivated")
    await db.users.update_one({"id": t["id"]}, {"$set": {"status": status, "status_changed_at": now_iso()}})
    if status == "deactivated":
        await revoke_user_sessions(t["id"])
    await audit(user["id"], f"team.member_{status}", {"user_id": t["id"]})
    return (await _serialize([await db.users.find_one({"id": t["id"]}, P)], await _depts(user["org_id"])))[0]


@router.post("/team/members/{member_id}/deactivate")
async def deactivate(member_id: str, user: dict = Depends(admin_only)):
    return await _set_status(user, member_id, "deactivated")


@router.post("/team/members/{member_id}/reactivate")
async def reactivate(member_id: str, user: dict = Depends(admin_only)):
    return await _set_status(user, member_id, "active")


class DeptIn(BaseModel):
    name: str = ""


async def _dept_name(user: dict, name: str, exclude: str | None = None) -> str:
    name = name.strip()
    if not name or len(name) > 60:
        raise field_error(422, {"name": "Enter a department name (up to 60 characters)"})
    q = {"org_id": user["org_id"], "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
    if exclude:
        q["id"] = {"$ne": exclude}
    if await db.departments.find_one(q, {"_id": 1}):
        raise field_error(422, {"name": "A department with this name already exists"})
    return name


@router.post("/org/departments", tags=["organisation"])
async def create_department(body: DeptIn, user: dict = Depends(admin_only)):
    name = await _dept_name(user, body.name)
    did, now = new_id("dep"), now_iso()
    await db.departments.insert_one({"id": did, "org_id": user["org_id"], "name": name, "manager_id": None, "created_at": now})
    await db.allocations.insert_one({"id": new_id("alc"), "scope_type": "department", "scope_id": did, "credits": 0,
                                     "period": "monthly", "created_at": now})
    await audit(user["id"], "org.department_created", {"department_id": did, "name": name})
    return {"id": did, "name": name}


@router.patch("/org/departments/{department_id}", tags=["organisation"])
async def rename_department(department_id: str, body: DeptIn, user: dict = Depends(admin_only)):
    if not await db.departments.find_one({"id": department_id, "org_id": user["org_id"]}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Department not found")
    name = await _dept_name(user, body.name, department_id)
    await db.departments.update_one({"id": department_id}, {"$set": {"name": name}})
    await audit(user["id"], "org.department_renamed", {"department_id": department_id, "name": name})
    return {"id": department_id, "name": name}
