from fastapi import HTTPException
from pymongo import ReturnDocument
from core.db import db, new_id, now_iso
from core.locks import locked
from services.actions import parse_credits, bad_request, conflict, history, notify
from services.usage import (window, usage_rows, total, allocation_map, members_usage, group, utilisation, health, prorate,
                            NEAR_LIMIT, UNDERUTILISED)
from services.users import audit
from services.validation import field_error

DEPT_EXCEEDS = "Department budgets exceed organisation budget"
ALLOC_EXCEEDS = "Allocations exceed department budget"
NOT_ENOUGH_POOL = "Not enough unallocated department budget"
URGENCY = ("low", "normal", "high")
P = {"_id": 0}


async def _alloc(scope_type: str, scope_id: str) -> int:
    return (await allocation_map(scope_type, [scope_id])).get(scope_id, 0)


async def _set_alloc(scope_type: str, scope_id: str, credits: int) -> None:
    await db.allocations.update_one(
        {"scope_type": scope_type, "scope_id": scope_id},
        {"$set": {"credits": credits, "updated_at": now_iso()},
         "$setOnInsert": {"id": new_id("alc"), "period": "monthly", "created_at": now_iso()}}, upsert=True)


async def _inc_alloc(user_id: str, delta: int) -> None:
    await db.allocations.update_one(
        {"scope_type": "user", "scope_id": user_id},
        {"$inc": {"credits": delta}, "$set": {"updated_at": now_iso()},
         "$setOnInsert": {"id": new_id("alc"), "period": "monthly", "created_at": now_iso()}}, upsert=True)


async def dept_allocated(dept_id: str) -> int:
    ids = [u["id"] async for u in db.users.find({"department_id": dept_id}, {"_id": 0, "id": 1})]
    return sum((await allocation_map("user", ids)).values())


async def used_30(user_id: str) -> int:
    return total(await usage_rows({"user_id": user_id}, window(30)))


async def _dept(user: dict, dept_id: str) -> dict:
    dept = await db.departments.find_one({"id": dept_id, "org_id": user["org_id"]}, P)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if user["role"] == "manager" and dept["id"] != user["department_id"]:
        raise HTTPException(status_code=403, detail="Managers can only manage their own department")
    return dept


async def _member(user: dict, member_id: str) -> dict:
    m = await db.users.find_one({"id": member_id, "org_id": user["org_id"]}, {"_id": 0, "password_hash": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found in your organisation")
    if user["role"] == "manager" and m.get("department_id") != user["department_id"]:
        raise HTTPException(status_code=403, detail="Managers can only manage their own department")
    if not m.get("department_id"):
        raise bad_request("This member has no department")
    return m


def _pair(sources: list[dict], targets: list[dict], out: list[dict], cross: bool, room: dict | None = None) -> None:
    for t in targets:
        if not sources:
            break
        s = max(sources, key=lambda x: x["unused"])
        amount = int(min(s["unused"] * 0.5, max(t["monthly_allocation"] * 0.2, 100)) // 50 * 50)
        if cross and room is not None:
            amount = min(amount, int(room.get(t["department_id"], 0)) // 50 * 50)
        if amount < 50:
            continue
        if cross and room is not None:
            room[t["department_id"]] = room.get(t["department_id"], 0) - amount
        s["unused"] -= amount
        if s["unused"] < 50:
            sources.remove(s)
        reason = f"{s['name'].split()[0]} is at {s['utilisation']}% while {t['name'].split()[0]} is at {t['utilisation']}%"
        if cross:
            reason += f" (moves budget from {s.get('department')} to {t.get('department')})"
        out.append({"from_user_id": s["id"], "from_name": s["name"], "to_user_id": t["id"], "to_name": t["name"],
                    "department": t["department"], "from_department": s.get("department"), "cross_department": cross,
                    "credits": amount, "reason": reason})


def _suggestions(members: list[dict], allow_cross: bool = False, room: dict | None = None) -> list[dict]:
    """Pair underused members with members near their limit: same department first, then (admins only) across departments."""
    out: list[dict] = []
    by_dept: dict = {}
    for m in members:
        by_dept.setdefault(m["department_id"], []).append(m)
    pools = {}
    for dept_id, dept_members in by_dept.items():
        sources = [dict(m) for m in dept_members if m["health"] == "underutilised" and m["unused"] > 0]
        targets = sorted([m for m in dept_members if m["health"] == "near_limit"], key=lambda m: -m["utilisation"])
        _pair(sources, targets, out, False)
        pools[dept_id] = sources
    if allow_cross:
        helped = {o["to_user_id"] for o in out}
        sources = [s for pool in pools.values() for s in pool]
        targets = sorted([m for m in members if m["health"] == "near_limit" and m["id"] not in helped], key=lambda m: -m["utilisation"])
        _pair(sources, targets, out, True, dict(room or {}))
    return out[:6]


async def _requests(query: dict) -> list[dict]:
    docs = await db.resource_requests.find(query, P).sort("created_at", -1).to_list(500)
    ids = {d["requester_id"] for d in docs} | {d.get("decided_by") for d in docs if d.get("decided_by")}
    names = {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1})}
    depts = {d["id"]: d["name"] async for d in db.departments.find({}, {"_id": 0, "id": 1, "name": 1})}
    return [{**d, "urgency": d.get("urgency", "normal"), "requester_name": names.get(d["requester_id"]),
             "department": depts.get(d.get("department_id")), "decided_by_name": names.get(d.get("decided_by")),
             "approved_credits": d.get("approved_credits", d["credits"] if d["status"] == "approved" else None)} for d in docs]


async def overview(user: dict, days: int) -> dict:
    role = user["role"]
    if role == "employee":
        rows = await usage_rows({"user_id": user["id"]}, window(days))
        me = (await members_usage({"id": user["id"]}, rows, days))[0]
        me["remaining"] = me["allocation"] - me["credits"]
        return {"role": role, "days": days, "simulated": True, "me": me,
                "requests": await _requests({"requester_id": user["id"]})}
    scope = {"org_id": user["org_id"]} if role == "admin" else {"department_id": user["department_id"]}
    rows = await usage_rows(scope, window(days))
    rows30 = rows if days == 30 else await usage_rows(scope, window(30))
    used30 = group(rows30, "user_id")
    members = await members_usage(scope, rows, days)
    users = {u["id"]: u async for u in db.users.find(scope, {"_id": 0, "id": 1, "department_id": 1})}
    for m in members:
        m["department_id"] = users[m["id"]].get("department_id")
        m["remaining"] = m["allocation"] - m["credits"]
        m["unused"] = max(0, m["monthly_allocation"] - used30.get(m["id"], {}).get("credits", 0))
    dq = {"org_id": user["org_id"], **({"id": user["department_id"]} if role == "manager" else {})}
    depts = await db.departments.find(dq, P).sort("name", 1).to_list(100)
    budgets = await allocation_map("department", [d["id"] for d in depts])
    by_dept = group(rows, "department_id")
    departments = []
    for d in depts:
        dm = [m for m in members if m["department_id"] == d["id"]]
        allocated = sum(m["monthly_allocation"] for m in dm)
        budget = budgets.get(d["id"], 0)
        used = by_dept.get(d["id"], {}).get("credits", 0)
        departments.append({"id": d["id"], "name": d["name"], "budget": budget, "allocated": allocated,
                            "unallocated": budget - allocated, "used": used, "members": len(dm),
                            "utilisation": utilisation(used, prorate(budget, days)), "health": health(used, prorate(budget, days))})
    out = {"role": role, "days": days, "simulated": True, "departments": departments, "members": members,
           "suggestions": _suggestions(members, allow_cross=role == "admin", room={d["id"]: max(0, d["unallocated"]) for d in departments}), "thresholds": {"underutilised": UNDERUTILISED, "near_limit": NEAR_LIMIT},
           "requests": await _requests({"org_id": user["org_id"], **({"department_id": user["department_id"]} if role == "manager" else {})}),
           "org": None}
    if role == "admin":
        org_budget = await _alloc("org", user["org_id"])
        dept_total = sum(budgets.values())
        out["org"] = {"budget": org_budget, "departments_total": dept_total, "unallocated": org_budget - dept_total}
    return out


async def set_org_budget(user: dict, credits) -> None:
    n = parse_credits(credits, "credits", minimum=0)
    async with locked(f"org:{user['org_id']}"):
        depts = [d["id"] async for d in db.departments.find({"org_id": user["org_id"]}, {"_id": 0, "id": 1})]
        if sum((await allocation_map("department", depts)).values()) > n:
            raise field_error(400, {"credits": DEPT_EXCEEDS})
        old = await _alloc("org", user["org_id"])
        await _set_alloc("org", user["org_id"], n)
    await audit(user["id"], "allocation.org_budget.updated", {"org_id": user["org_id"], "from": old, "to": n})
    await notify(user["id"], "allocation.org_budget", f"Organisation budget set to {n:,} credits", {"org_id": user["org_id"]})


async def set_dept_budget(user: dict, dept_id: str, credits) -> None:
    n = parse_credits(credits, "credits", minimum=0)
    dept = await _dept(user, dept_id)
    async with locked(f"org:{user['org_id']}", f"dept:{dept_id}"):
        others = [d["id"] async for d in db.departments.find({"org_id": user["org_id"], "id": {"$ne": dept_id}}, {"_id": 0, "id": 1})]
        if sum((await allocation_map("department", others)).values()) + n > await _alloc("org", user["org_id"]):
            raise field_error(400, {"credits": DEPT_EXCEEDS})
        if await dept_allocated(dept_id) > n:
            raise field_error(400, {"credits": ALLOC_EXCEEDS})
        old = await _alloc("department", dept_id)
        await _set_alloc("department", dept_id, n)
    await audit(user["id"], "allocation.department_budget.updated", {"department_id": dept_id, "from": old, "to": n})
    if dept.get("manager_id"):
        await notify(dept["manager_id"], "allocation.department_budget", f"{dept['name']} budget set to {n:,} credits", {"department_id": dept_id})


async def set_member_allocation(user: dict, member_id: str, credits) -> None:
    n = parse_credits(credits, "credits", minimum=0)
    m = await _member(user, member_id)
    async with locked(f"dept:{m['department_id']}"):
        current = await _alloc("user", member_id)
        if await dept_allocated(m["department_id"]) - current + n > await _alloc("department", m["department_id"]):
            raise field_error(400, {"credits": ALLOC_EXCEEDS})
        await _set_alloc("user", member_id, n)
    await audit(user["id"], "allocation.member.updated", {"member_id": member_id, "from": current, "to": n})
    await notify(member_id, "allocation.updated", f"Your monthly allocation is now {n:,} credits", {"from": current, "to": n})


async def reallocate(user: dict, from_id: str, to_id: str, credits) -> None:
    if from_id == to_id:
        raise bad_request("Choose two different members")
    n = parse_credits(credits, "credits")
    src = await _member(user, from_id)
    dst = await _member(user, to_id)
    async with locked(f"dept:{src['department_id']}", f"dept:{dst['department_id']}"):
        await _move(src, dst, n)
    meta = {"from_user_id": from_id, "to_user_id": to_id, "credits": n}
    await audit(user["id"], "allocation.reallocated", meta)
    await notify(from_id, "allocation.reallocated", f"{n:,} credits were moved from your allocation to {dst['name']}", meta)
    await notify(to_id, "allocation.reallocated", f"{n:,} credits were added to your allocation from {src['name']}", meta)


async def _move(src: dict, dst: dict, n: int) -> None:
    from_id, to_id = src["id"], dst["id"]
    used = await used_30(from_id)
    src_alloc = await _alloc("user", from_id)
    unused = max(0, src_alloc - used)
    if n > unused:
        raise field_error(400, {"credits": f"Amount exceeds {src['name'].split()[0]}'s unused allocation ({unused:,} credits)"})
    if src["department_id"] != dst["department_id"]:
        room = await _alloc("department", dst["department_id"]) - await dept_allocated(dst["department_id"])
        if n > room:
            raise field_error(400, {"credits": ALLOC_EXCEEDS})
    done = await db.allocations.find_one_and_update(
        {"scope_type": "user", "scope_id": from_id, "credits": {"$gte": used + n}},
        {"$inc": {"credits": -n}, "$set": {"updated_at": now_iso()}}, return_document=ReturnDocument.AFTER)
    if not done:
        raise conflict("The source allocation changed. Refresh and try again.")
    await _inc_alloc(to_id, n)


async def create_request(user: dict, amount, reason: str, urgency: str) -> dict:
    if user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only employees can submit resource requests")
    errors = {}
    try:
        n = parse_credits(amount)
    except HTTPException as exc:
        errors.update(exc.detail["fields"])
    if not reason.strip():
        errors["reason"] = "Add a reason for the request"
    if urgency not in URGENCY:
        errors["urgency"] = "Choose low, normal or high"
    if errors:
        raise field_error(422, errors)
    doc = {"id": new_id("req"), "org_id": user["org_id"], "requester_id": user["id"], "department_id": user["department_id"],
           "credits": n, "reason": reason.strip(), "urgency": urgency, "status": "pending", "created_at": now_iso(),
           "history": [history(user["id"], "submitted", amount=n)]}
    await db.resource_requests.insert_one(doc)
    dept = await db.departments.find_one({"id": user["department_id"]}, P)
    approvers = {dept.get("manager_id")} | {a["id"] async for a in db.users.find({"org_id": user["org_id"], "role": "admin"}, {"_id": 0, "id": 1})}
    for uid in approvers - {None}:
        await notify(uid, "allocation.request", f"{user['name']} requested {n:,} credits ({urgency})", {"request_id": doc["id"]})
    await audit(user["id"], "allocation.request.created", {"request_id": doc["id"], "credits": n, "urgency": urgency})
    return (await _requests({"id": doc["id"]}))[0]


async def _scoped_request(user: dict, request_id: str) -> dict:
    req = await db.resource_requests.find_one({"id": request_id, "org_id": user["org_id"]}, P)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if user["role"] == "manager" and req["department_id"] != user["department_id"]:
        raise HTTPException(status_code=403, detail="Managers can only manage their own department")
    if user["role"] == "employee" and req["requester_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only manage your own requests")
    return req


async def _decide(request_id: str, status: str, actor_id: str, fields: dict) -> None:
    done = await db.resource_requests.find_one_and_update(
        {"id": request_id, "status": "pending"},
        {"$set": {"status": status, "decided_at": now_iso(), **fields}, "$push": {"history": history(actor_id, status)}})
    if not done:
        raise conflict()


async def approve_request(user: dict, request_id: str, credits) -> dict:
    req = await _scoped_request(user, request_id)
    if req["status"] != "pending":
        raise conflict()
    n = req["credits"] if credits in (None, "") else parse_credits(credits, "credits")
    if n > req["credits"]:
        raise field_error(400, {"credits": f"Approve between 1 and {req['credits']:,} credits"})
    async with locked(f"dept:{req['department_id']}"):
        pool = await _alloc("department", req["department_id"]) - await dept_allocated(req["department_id"])
        if n > pool:
            raise field_error(400, {"credits": NOT_ENOUGH_POOL})
        await _decide(request_id, "approved", user["id"], {"approved_credits": n, "decided_by": user["id"]})
        await _inc_alloc(req["requester_id"], n)
    await notify(req["requester_id"], "allocation.request.approved", f"Your request was approved for {n:,} credits", {"request_id": request_id})
    await audit(user["id"], "allocation.request.approved", {"request_id": request_id, "credits": n, "requested": req["credits"]})
    return (await _requests({"id": request_id}))[0]


async def reject_request(user: dict, request_id: str, note: str) -> dict:
    await _scoped_request(user, request_id)
    await _decide(request_id, "rejected", user["id"], {"decision_note": note.strip(), "decided_by": user["id"]})
    rq = (await _requests({"id": request_id}))[0]
    await notify(rq["requester_id"], "allocation.request.rejected", "Your resource request was rejected", {"request_id": request_id, "note": note.strip()})
    await audit(user["id"], "allocation.request.rejected", {"request_id": request_id, "note": note.strip()})
    return rq


async def cancel_request(user: dict, request_id: str) -> dict:
    req = await _scoped_request(user, request_id)
    if req["requester_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the requester can cancel this request")
    await _decide(request_id, "cancelled", user["id"], {})
    await audit(user["id"], "allocation.request.cancelled", {"request_id": request_id})
    manager = (await db.departments.find_one({"id": req["department_id"]}, P) or {}).get("manager_id")
    admins = {a["id"] async for a in db.users.find({"org_id": user["org_id"], "role": "admin"}, {"_id": 0, "id": 1})}
    for uid in ({manager} | admins) - {None}:
        await notify(uid, "allocation.request.cancelled", f"{user['name']} cancelled a {req['credits']:,} credit request", {"request_id": request_id})
    return (await _requests({"id": request_id}))[0]
