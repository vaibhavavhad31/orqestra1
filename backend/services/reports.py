import csv
import io
from core.db import db
from services.lending import list_entries, summary as lending_summary
from services.overview import admin_overview, manager_overview, personal_overview
from services.usage import (scoped_usage, scope_for, load_providers, daily_series, window, members_usage, group,
                            health, utilisation)

SIMULATED = "Simulated data"


async def _scope_label(user: dict, scope_type: str) -> str:
    if scope_type == "organisation":
        return (await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0, "name": 1}))["name"]
    if scope_type == "department":
        return (await db.departments.find_one({"id": user["department_id"]}, {"_id": 0, "name": 1}))["name"]
    return user["name"]


async def usage_report(user: dict, days: int) -> dict:
    scope = scope_for(user)
    rows, payload = await scoped_usage(scope["match"], days)
    providers = await load_providers()
    daily = [{"date": d["date"], "credits": d["total"]} for d in daily_series(rows, window(days), providers)]
    out = {"kind": "usage", "label": SIMULATED, "simulated": True, "days": days, "start": payload["start"], "end": payload["end"],
           "scope": {"type": scope["type"], "label": await _scope_label(user, scope["type"])},
           "totals": payload["totals"], "providers": payload["providers"], "timeseries": payload["timeseries"],
           "granularity": payload["granularity"], "daily": daily, "members": None, "departments": None}
    if scope["type"] != "self":
        out["members"] = [{k: m[k] for k in ("id", "name", "department", "role", "credits", "requests", "top_provider")}
                          for m in await members_usage(scope["match"], rows, days)]
    if scope["type"] == "organisation":
        g = group(rows, "department_id")
        depts = await db.departments.find({"org_id": user["org_id"]}, {"_id": 0, "id": 1, "name": 1}).sort("name", 1).to_list(100)
        out["departments"] = [{"id": d["id"], "name": d["name"], "credits": g.get(d["id"], {}).get("credits", 0),
                               "requests": g.get(d["id"], {}).get("requests", 0)} for d in depts]
    return out


def _row(name: str, level: str, budget: int, allocated: int, used: int) -> dict:
    return {"name": name, "level": level, "budget": budget, "allocated": allocated, "used": used,
            "remaining": budget - used, "utilisation": utilisation(used, budget), "status": health(used, budget)}


async def allocation_report(user: dict, days: int) -> dict:
    base = {"kind": "allocation", "label": SIMULATED, "simulated": True, "days": days}
    if user["role"] == "admin":
        ov = await admin_overview(user, days)
        rows = [_row(ov["organization"]["name"], "Organisation", ov["cycle"]["budget"], ov["cycle"]["allocated"], ov["cycle"]["used"])]
        rows += [_row(d["name"], "Department", d["allocation"], d["allocation"], d["used"]) for d in ov["departments"]]
        return {**base, "start": ov["start"], "end": ov["end"], "scope": {"type": "organisation", "label": ov["organization"]["name"]},
                "totals": ov["totals"], "rows": rows}
    ov = await manager_overview(user, days)
    members = ov["members"]
    rows = [_row(ov["department"]["name"], "Department", ov["cycle"]["budget"], sum(m["allocation"] for m in members), ov["cycle"]["used"])]
    rows += [_row(m["name"], "Member", m["allocation"], m["allocation"], m["credits"]) for m in members]
    return {**base, "start": ov["start"], "end": ov["end"], "scope": {"type": "department", "label": ov["department"]["name"]},
            "totals": ov["totals"], "rows": rows}


async def lending_report(user: dict, days: int) -> dict:
    ov = await personal_overview(user, days)
    entries = await list_entries(user["id"])
    return {"kind": "lending", "label": SIMULATED, "simulated": True, "days": days, "start": ov["start"], "end": ov["end"],
            "scope": {"type": "self", "label": user["name"]}, "totals": ov["totals"], "cycle": ov["cycle"],
            "summary": await lending_summary(user["id"]),
            "entries": [{"id": e["id"], "counterparty": e["counterparty_name"], "direction": e["direction"], "credits": e["credits"],
                         "repaid": e.get("repaid_credits", 0), "outstanding": e["outstanding"], "status": e["status"],
                         "due_date": e.get("due_date"), "created_at": e["created_at"][:10]} for e in entries]}


def to_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([SIMULATED, f"{report['kind'].title()} report", report["scope"]["label"], f"{report['start']} to {report['end']}",
                f"Last {report['days']} days"])
    w.writerow([])

    def section(title: str, headers: list[str], rows: list[list]):
        w.writerow([title])
        w.writerow(headers)
        w.writerows(rows)
        w.writerow([])

    if report["kind"] == "usage":
        section("By provider", ["Provider", "Credits", "Requests", "Share %"],
                [[p["name"], p["credits"], p["requests"], p["share"]] for p in report["providers"]])
        if report["departments"]:
            section("By department", ["Department", "Credits", "Requests"], [[d["name"], d["credits"], d["requests"]] for d in report["departments"]])
        if report["members"]:
            section("By member", ["Member", "Department", "Role", "Credits", "Requests"],
                    [[m["name"], m["department"] or "", m["role"], m["credits"], m["requests"]] for m in report["members"]])
        section("Daily totals", ["Date", "Credits"], [[d["date"], d["credits"]] for d in report["daily"]])
    elif report["kind"] == "allocation":
        section("Allocation", ["Name", "Level", "Budget", "Allocated", "Used", "Remaining", "Utilisation %", "Status"],
                [[r["name"], r["level"], r["budget"], r["allocated"], r["used"], r["remaining"], r["utilisation"], r["status"]] for r in report["rows"]])
    else:
        s = report["summary"]
        section("Lending summary", ["Lent outstanding", "Borrowed outstanding", "Net", "Active loans", "Pending", "Overdue"],
                [[s["lent_outstanding"], s["borrowed_outstanding"], s["net"], s["active_loans"], s["pending_requests"], s["overdue"]]])
        section("Entries", ["Counterparty", "Direction", "Credits", "Repaid", "Outstanding", "Status", "Due date", "Created"],
                [[e["counterparty"], e["direction"], e["credits"], e["repaid"], e["outstanding"], e["status"], e["due_date"] or "", e["created_at"]]
                 for e in report["entries"]])
    w.writerow(["Total credits used", report["totals"]["credits"]])
    return buf.getvalue()
