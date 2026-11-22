"""Reconciliation check: run `python scripts/reconcile.py` from /app/backend (server must be running)."""
import sys
import httpx

API = "http://localhost:8001/api"
ok = True


def check(cond: bool, msg: str) -> None:
    global ok
    if not cond:
        ok = False
        print("FAIL", msg)


def cycle_ok(c: dict, label: str) -> None:
    check(c["budget"] == c["used"] + c["remaining"], f"{label} budget != used + remaining {c}")
    exp = round(c["used"] / c["budget"] * 100, 1) if c["budget"] else 0.0
    check(c["utilisation"] == exp, f"{label} utilisation {c['utilisation']} != {exp}")


for key in ("admin", "manager", "employee", "individual"):
    client = httpx.Client(base_url=API)
    token = client.post("/demo/login", json={"key": key}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    for days in (7, 30, 90):
        ov = client.get("/overview", params={"days": days}, headers=h).json()
        us = client.get("/usage", params={"days": days}, headers=h).json()
        tag = f"{key}/{days}d"
        cycle_ok(ov["cycle"], tag)
        total = us["totals"]["credits"]
        check(ov["totals"]["credits"] == total == ov["cycle"]["used"], f"{tag} overview vs usage total")
        check(sum(p["credits"] for p in us["providers"]) == total, f"{tag} provider sum")
        check(sum(b["total"] for b in us["timeseries"]) == total, f"{tag} timeseries sum")
        check(sum(b["credits"] for b in ov["trend"]) == total, f"{tag} overview trend sum")
        check(us["granularity"] == ("week" if days == 90 else "day"), f"{tag} granularity")
        if us["members"] is not None:
            check(sum(m["credits"] for m in us["members"]) == total, f"{tag} member sum")
        if key == "admin":
            check(sum(d["credits"] for d in us["departments"]) == total, f"{tag} department sum (usage)")
            check(sum(d["used"] for d in ov["departments"]) == total, f"{tag} department sum (overview)")
            for d in ov["departments"]:
                du = client.get("/usage", params={"days": days, "department_id": d["id"]}, headers=h).json()
                check(du["totals"]["credits"] == d["used"], f"{tag} dept filter {d['name']}")
                check(sum(m["credits"] for m in du["members"]) == d["used"], f"{tag} dept members {d['name']}")
        if key == "manager":
            check(sum(m["credits"] for m in ov["members"]) == total, f"{tag} manager overview members")
        for p in us["providers"]:
            pu = client.get("/usage", params={"days": days, "provider": p["id"]}, headers=h).json()
            check(pu["totals"]["credits"] == p["credits"], f"{tag} provider filter {p['id']}")
        if key == "individual":
            check("organization" not in ov and "departments" not in ov, f"{tag} individual leaks org data")
    print(key, "checked")

# --- Phase 2: allocation sums and lending balances, recomputed straight from the database ---
from pathlib import Path
from pymongo import MongoClient
env = dict(l.strip().split("=", 1) for l in Path(__file__).resolve().parent.parent.joinpath(".env").read_text().splitlines() if "=" in l)
db = MongoClient(env["MONGO_URL"].strip('"'))[env["DB_NAME"].strip('"')]
alloc = {(a["scope_type"], a["scope_id"]): a["credits"] for a in db.allocations.find({}, {"_id": 0})}
for org in db.organizations.find({}, {"_id": 0}):
    depts = list(db.departments.find({"org_id": org["id"]}, {"_id": 0}))
    dept_sum = sum(alloc.get(("department", d["id"]), 0) for d in depts)
    check(dept_sum <= alloc.get(("org", org["id"]), 0), f"{org['name']}: department budgets {dept_sum} exceed org budget")
    for d in depts:
        members = sum(alloc.get(("user", u["id"]), 0) for u in db.users.find({"department_id": d["id"]}, {"_id": 0, "id": 1}))
        check(members <= alloc.get(("department", d["id"]), 0), f"{d['name']}: member allocations {members} exceed budget")
for loan in db.lending_ledger.find({}, {"_id": 0}):
    confirmed = sum(r["amount"] for r in db.lending_repayments.find({"loan_id": loan["id"], "status": "confirmed"}))
    check(loan.get("repaid_credits", 0) == confirmed, f"{loan['id']}: repaid {loan.get('repaid_credits')} != confirmed {confirmed}")
    check(0 <= loan["credits"] - loan.get("repaid_credits", 0), f"{loan['id']}: negative outstanding")
    if loan["status"] == "repaid":
        check(loan["repaid_credits"] == loan["credits"], f"{loan['id']}: repaid but outstanding > 0")
    if loan["status"] == "active":
        check(loan.get("repaid_credits", 0) < loan["credits"], f"{loan['id']}: active with nothing outstanding")
for key in ("individual", "tomas", "hana", "kwame"):
    client = httpx.Client(base_url=API)
    r = client.post("/demo/login", json={"key": key}).json()
    h = {"Authorization": f"Bearer {r['access_token']}"}
    uid = r["user"]["id"]
    s = client.get("/lending/summary", headers=h).json()
    loans = list(db.lending_ledger.find({"$or": [{"lender_id": uid}, {"borrower_id": uid}], "status": "active"}, {"_id": 0}))
    lent = sum(l["credits"] - l["repaid_credits"] for l in loans if l["lender_id"] == uid)
    borrowed = sum(l["credits"] - l["repaid_credits"] for l in loans if l["borrower_id"] == uid)
    used30 = client.get("/overview", params={"days": 30}, headers=h).json()["cycle"]["used"]
    check((s["lent_outstanding"], s["borrowed_outstanding"]) == (lent, borrowed), f"lending {key}: summary vs ledger")
    check(s["available"] == alloc.get(("user", uid), 0) - used30 - lent + borrowed, f"lending {key}: available formula")
    check(s["used"] == used30, f"lending {key}: used vs overview")
print("phase 2 checks done")

print("ALL OK" if ok else "FAILURES")
sys.exit(0 if ok else 1)
