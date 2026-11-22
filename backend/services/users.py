from core.db import db, new_id, now_iso
from core.deps import PUBLIC_USER
from core.permissions import allowed_modules, ROLE_LABELS
from core.config import DEFAULT_ORG_BUDGET, DEFAULT_PERSONAL_CREDITS
from models.schemas import UserOut


async def get_user(user_id: str) -> dict | None:
    return await db.users.find_one({"id": user_id}, PUBLIC_USER)


async def serialize_user(user: dict) -> UserOut:
    org = dept = None
    if user.get("org_id"):
        org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0, "id": 1, "name": 1})
    if user.get("department_id"):
        dept = await db.departments.find_one({"id": user["department_id"]}, {"_id": 0, "id": 1, "name": 1})
    return UserOut(
        **user,
        role_label=ROLE_LABELS[user["role"]],
        organization=org,
        department=dept,
        allowed_modules=allowed_modules(user["role"]),
    )


async def audit(actor_id: str | None, action: str, meta: dict | None = None) -> None:
    await db.audit_log.insert_one({"id": new_id("aud"), "actor_id": actor_id, "action": action,
                                   "meta": meta or {}, "created_at": now_iso()})


async def create_account(*, name: str, email: str, mode: str, org_name: str,
                         auth_provider: str, password_hash: str | None = None, picture: str | None = None) -> dict:
    now = now_iso()
    uid = new_id("usr")
    user = {"id": uid, "email": email, "name": name, "title": None, "mode": mode,
            "role": "individual", "org_id": None, "department_id": None, "is_demo": False,
            "auth_provider": auth_provider, "picture": picture, "created_at": now}
    if password_hash:
        user["password_hash"] = password_hash
    if mode == "organisation":
        org_id = new_id("org")
        await db.organizations.insert_one({"id": org_id, "name": org_name, "owner_id": uid,
                                           "is_demo": False, "created_at": now})
        await db.allocations.insert_one({"id": new_id("alc"), "scope_type": "org", "scope_id": org_id,
                                         "credits": DEFAULT_ORG_BUDGET, "period": "monthly", "created_at": now})
        user.update(role="admin", org_id=org_id, title="Organisation Admin")
    else:
        await db.allocations.insert_one({"id": new_id("alc"), "scope_type": "user", "scope_id": uid,
                                         "credits": DEFAULT_PERSONAL_CREDITS, "period": "monthly", "created_at": now})
    await db.users.insert_one(user)
    await audit(uid, "account.created", {"mode": mode, "auth_provider": auth_provider})
    return await get_user(uid)
