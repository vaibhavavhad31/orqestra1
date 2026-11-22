from core.db import db
from services.lending import summary as lending_summary
from services.usage import (scoped_usage, prorate, utilisation, health, allocation_map, members_usage,
                            group, top_provider)


def _cycle(budget: int, used: int) -> dict:
    return {"budget": budget, "used": used, "remaining": budget - used, "utilisation": utilisation(used, budget)}


async def _base(match: dict, days: int):
    rows, payload = await scoped_usage(match, days)
    series = payload.pop("timeseries")
    payload["trend"] = [{"date": d["date"], "end": d.get("end"), "credits": d["total"]} for d in series]
    return rows, payload


async def admin_overview(user: dict, days: int) -> dict:
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0})
    rows, base = await _base({"org_id": org["id"]}, days)
    budget = (await allocation_map("org", [org["id"]])).get(org["id"], 0)
    depts = await db.departments.find({"org_id": org["id"]}, {"_id": 0}).sort("name", 1).to_list(100)
    dept_alloc = await allocation_map("department", [d["id"] for d in depts])
    by_dept = group(rows, "department_id")
    headcount = await db.users.count_documents({"org_id": org["id"], "status": {"$ne": "deactivated"}})
    members = await members_usage({"org_id": org["id"]}, rows, days)
    departments = []
    for d in depts:
        used = by_dept.get(d["id"], {}).get("credits", 0)
        alloc = prorate(dept_alloc.get(d["id"], 0), days)
        departments.append({"id": d["id"], "name": d["name"], "allocation": alloc, "used": used,
                            "utilisation": utilisation(used, alloc), "health": health(used, alloc),
                            "members": sum(1 for m in members if m["department"] == d["name"])})
    attention = [m for m in members if m["health"] in ("near_limit", "underutilised")]
    return {**base, "role": "admin",
            "organization": {"id": org["id"], "name": org["name"], "employees": headcount, "departments": len(depts),
                             "monthly_budget": budget},
            "cycle": {**_cycle(prorate(budget, days), base["totals"]["credits"]),
                      "allocated": prorate(sum(dept_alloc.values()), days)},
            "departments": departments,
            "health": {"near_limit": sum(1 for m in members if m["health"] == "near_limit"),
                       "underutilised": sum(1 for m in members if m["health"] == "underutilised"),
                       "attention": sorted(attention, key=lambda m: -m["utilisation"])}}


async def manager_overview(user: dict, days: int) -> dict:
    dept = await db.departments.find_one({"id": user["department_id"]}, {"_id": 0})
    rows, base = await _base({"department_id": dept["id"]}, days)
    alloc = prorate((await allocation_map("department", [dept["id"]])).get(dept["id"], 0), days)
    members = await members_usage({"department_id": dept["id"]}, rows, days)
    return {**base, "role": "manager",
            "department": {"id": dept["id"], "name": dept["name"], "members": len(members)},
            "cycle": _cycle(alloc, base["totals"]["credits"]), "members": members}


async def personal_overview(user: dict, days: int) -> dict:
    rows, base = await _base({"user_id": user["id"]}, days)
    alloc = prorate((await allocation_map("user", [user["id"]])).get(user["id"], 0), days)
    g = group(rows, "user_id").get(user["id"])
    out = {**base, "role": user["role"], "cycle": _cycle(alloc, base["totals"]["credits"]),
           "top_provider": top_provider(g)}
    if user["role"] == "individual":
        out["lending"] = await lending_summary(user["id"])
    return out


async def build_overview(user: dict, days: int) -> dict:
    if user["role"] == "admin":
        return await admin_overview(user, days)
    if user["role"] == "manager":
        return await manager_overview(user, days)
    return await personal_overview(user, days)
