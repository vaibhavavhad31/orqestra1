from fastapi import APIRouter, Depends, HTTPException, Query
from core.db import db
from core.deps import require_module, get_current_user, forbidden
from services.overview import build_overview
from services.usage import check_days, scope_for, load_providers, scoped_usage, members_usage, group

router = APIRouter(tags=["dashboard"])


@router.get("/overview")
async def overview(days: int = Query(30), user: dict = Depends(require_module("overview"))):
    check_days(days)
    return await build_overview(user, days)


async def _scope_label(user: dict, scope_type: str) -> str:
    if scope_type == "organisation":
        org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0, "name": 1})
        return org["name"]
    if scope_type == "department":
        dept = await db.departments.find_one({"id": user["department_id"]}, {"_id": 0, "name": 1})
        return f"{dept['name']} department"
    return "Your usage"


async def _scoped_filters(user: dict, scope: dict, department_id: str | None, member_id: str | None) -> dict:
    """Returns the user filter for the requested department/member, refusing anything outside the caller's scope."""
    user_filter = dict(scope["match"])
    if (department_id or member_id) and scope["type"] == "self":
        raise forbidden("Department and member filters are not available for your role")
    if department_id:
        if scope["type"] != "organisation":
            raise forbidden("Only Admins can filter by department")
        if not await db.departments.find_one({"id": department_id, "org_id": user["org_id"]}, {"_id": 1}):
            raise forbidden("That department is outside your organisation")
        user_filter["department_id"] = department_id
    if member_id:
        if not await db.users.find_one({**user_filter, "id": member_id}, {"_id": 1}):
            raise forbidden("That member is outside your scope")
        user_filter["id"] = member_id
    return user_filter


async def _filter_options(user: dict, scope: dict) -> dict:
    opts = {"departments": [], "members": []}
    if scope["type"] == "organisation":
        opts["departments"] = await db.departments.find({"org_id": user["org_id"]}, {"_id": 0, "id": 1, "name": 1}).sort("name", 1).to_list(100)
    if scope["type"] != "self":
        opts["members"] = await db.users.find(scope["match"], {"_id": 0, "id": 1, "name": 1, "department_id": 1}).sort("name", 1).to_list(1000)
    return opts


@router.get("/usage")
async def usage(days: int = Query(30), provider: str | None = Query(None), department_id: str | None = Query(None),
                member_id: str | None = Query(None), user: dict = Depends(require_module("usage"))):
    check_days(days)
    scope = scope_for(user)
    providers = await load_providers()
    if provider and provider not in {p["id"] for p in providers}:
        raise HTTPException(status_code=400, detail="Unknown provider")
    user_filter = await _scoped_filters(user, scope, department_id, member_id)
    match = {**scope["match"], **({"department_id": department_id} if department_id else {}),
             **({"user_id": member_id} if member_id else {}), **({"provider_id": provider} if provider else {})}
    rows, payload = await scoped_usage(match, days, compare=True)
    out = {**payload, "scope": {"type": scope["type"], "label": await _scope_label(user, scope["type"])},
           "filters": {"provider": provider, "department_id": department_id, "member_id": member_id},
           "filter_options": await _filter_options(user, scope), "members": None, "departments": None}
    if scope["type"] != "self":
        out["members"] = await members_usage(user_filter, rows, days)
        if provider:
            for m in out["members"]:
                m.update(utilisation=None, health=None)
    if scope["type"] == "organisation" and not member_id:
        g = group(rows, "department_id")
        dq = {"org_id": user["org_id"], **({"id": department_id} if department_id else {})}
        depts = await db.departments.find(dq, {"_id": 0, "id": 1, "name": 1}).sort("name", 1).to_list(100)
        out["departments"] = [{"id": d["id"], "name": d["name"], "credits": g.get(d["id"], {}).get("credits", 0),
                               "requests": g.get(d["id"], {}).get("requests", 0)} for d in depts]
    return out


@router.get("/providers", tags=["providers"])
async def providers(_: dict = Depends(get_current_user)):
    return await load_providers()
