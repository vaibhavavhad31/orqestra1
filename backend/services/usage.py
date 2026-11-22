from datetime import timedelta
from fastapi import HTTPException
from core.db import db, today_utc

VALID_DAYS = (7, 30, 90)
NEAR_LIMIT = 0.85
UNDERUTILISED = 0.40


def check_days(days: int) -> None:
    if days not in VALID_DAYS:
        raise HTTPException(status_code=400, detail="days must be one of 7, 30 or 90")


def window(days: int, offset: int = 0) -> list[str]:
    start = today_utc() - timedelta(days=days - 1 + offset)
    return [(start + timedelta(days=i)).isoformat() for i in range(days)]


def bucketed(series: list[dict], days: int) -> tuple[str, list[dict]]:
    if days < 90:
        return "day", series
    out = []
    for i in range(0, len(series), 7):
        chunk = series[i:i + 7]
        bucket = {"date": chunk[0]["date"], "end": chunk[-1]["date"]}
        for key in chunk[0]:
            if key != "date":
                bucket[key] = sum(c[key] for c in chunk)
        out.append(bucket)
    return "week", out


async def scoped_usage(match: dict, days: int, compare: bool = False) -> tuple[list[dict], dict]:
    """Single calculation path shared by Overview and AI Usage."""
    dates = window(days)
    providers = await load_providers()
    rows = await usage_rows(match, dates)
    prev = await usage_rows(match, window(days, days)) if compare else None
    granularity, series = bucketed(daily_series(rows, dates, providers), days)
    return rows, {"days": days, "start": dates[0], "end": dates[-1], "simulated": True,
                  "granularity": granularity, "totals": summary_totals(rows, days, prev),
                  "providers": provider_breakdown(rows, providers), "timeseries": series}


def scope_for(user: dict) -> dict:
    if user["mode"] == "individual" or user["role"] == "employee":
        return {"type": "self", "match": {"user_id": user["id"]}}
    if user["role"] == "manager":
        return {"type": "department", "match": {"department_id": user["department_id"]}}
    return {"type": "organisation", "match": {"org_id": user["org_id"]}}


async def load_providers() -> list[dict]:
    return await db.providers.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(100)


async def usage_rows(match: dict, dates: list[str]) -> list[dict]:
    pipeline = [
        {"$match": {**match, "date": {"$gte": dates[0], "$lte": dates[-1]}}},
        {"$group": {"_id": {"d": "$date", "p": "$provider_id", "u": "$user_id", "dep": "$department_id"},
                    "credits": {"$sum": "$credits"}, "requests": {"$sum": "$requests"}}},
    ]
    rows = []
    async for r in db.usage_records.aggregate(pipeline):
        k = r["_id"]
        rows.append({"date": k["d"], "provider_id": k["p"], "user_id": k["u"], "department_id": k.get("dep"),
                     "credits": r["credits"], "requests": r["requests"]})
    return rows


def total(rows: list[dict], key: str = "credits") -> int:
    return sum(r[key] for r in rows)


def group(rows: list[dict], field: str) -> dict:
    acc: dict = {}
    for r in rows:
        a = acc.setdefault(r[field], {"credits": 0, "requests": 0, "providers": {}})
        a["credits"] += r["credits"]
        a["requests"] += r["requests"]
        a["providers"][r["provider_id"]] = a["providers"].get(r["provider_id"], 0) + r["credits"]
    return acc


def top_provider(entry: dict | None) -> str | None:
    if not entry or not entry["providers"]:
        return None
    return max(entry["providers"], key=entry["providers"].get)


def provider_breakdown(rows: list[dict], providers: list[dict]) -> list[dict]:
    g = group(rows, "provider_id")
    tot = total(rows) or 1
    out = []
    for p in providers:
        e = g.get(p["id"], {"credits": 0, "requests": 0})
        out.append({"id": p["id"], "name": p["name"], "vendor": p["vendor"], "color": p["color"],
                    "simulated": p["simulated"], "credits": e["credits"], "requests": e["requests"],
                    "share": round(e["credits"] / tot * 100, 1)})
    return out


def daily_series(rows: list[dict], dates: list[str], providers: list[dict]) -> list[dict]:
    idx = {d: {"date": d, "total": 0, **{p["id"]: 0 for p in providers}} for d in dates}
    for r in rows:
        day = idx.get(r["date"])
        if day is not None and r["provider_id"] in day:
            day[r["provider_id"]] += r["credits"]
            day["total"] += r["credits"]
    return list(idx.values())


def prorate(monthly: int, days: int) -> int:
    return round(monthly * days / 30)


def utilisation(used: int, alloc: int) -> float:
    return round(used / alloc * 100, 1) if alloc else 0.0


def health(used: int, alloc: int) -> str:
    if not alloc:
        return "unallocated"
    u = used / alloc
    return "near_limit" if u >= NEAR_LIMIT else "underutilised" if u < UNDERUTILISED else "healthy"


async def allocation_map(scope_type: str, ids) -> dict:
    docs = await db.allocations.find({"scope_type": scope_type, "scope_id": {"$in": list(ids)}}, {"_id": 0}).to_list(2000)
    return {d["scope_id"]: d["credits"] for d in docs}


async def members_usage(user_filter: dict, rows: list[dict], days: int) -> list[dict]:
    users = await db.users.find(user_filter, {"_id": 0, "id": 1, "name": 1, "title": 1, "role": 1, "department_id": 1}).sort("name", 1).to_list(1000)
    dept_ids = list({u.get("department_id") for u in users if u.get("department_id")})
    depts = {d["id"]: d["name"] async for d in db.departments.find({"id": {"$in": dept_ids}}, {"_id": 0, "id": 1, "name": 1})}
    allocs = await allocation_map("user", [u["id"] for u in users])
    g = group(rows, "user_id")
    out = []
    for u in users:
        e = g.get(u["id"])
        used = e["credits"] if e else 0
        alloc = prorate(allocs.get(u["id"], 0), days)
        out.append({"id": u["id"], "name": u["name"], "title": u.get("title"), "role": u["role"],
                    "department": depts.get(u.get("department_id")), "credits": used,
                    "requests": e["requests"] if e else 0, "top_provider": top_provider(e),
                    "monthly_allocation": allocs.get(u["id"], 0),
                    "allocation": alloc, "utilisation": utilisation(used, alloc), "health": health(used, alloc)})
    return out


def summary_totals(rows: list[dict], days: int, prev_rows: list[dict] | None = None) -> dict:
    credits = total(rows)
    out = {"credits": credits, "requests": total(rows, "requests"),
           "avg_per_day": round(credits / days), "active_days": len({r["date"] for r in rows})}
    if prev_rows is not None:
        prev = total(prev_rows)
        out["previous_credits"] = prev
        out["change_pct"] = round((credits - prev) / prev * 100, 1) if prev else None
    return out
