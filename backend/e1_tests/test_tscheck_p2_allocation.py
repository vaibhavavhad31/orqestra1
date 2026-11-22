import httpx, subprocess, uuid
from pymongo import MongoClient
from conftest import BASE, demo

P = lambda h, p, j=None: httpx.post(BASE + p, headers=h, json=j if j is not None else {})
PUT = lambda h, p, j: httpx.put(BASE + p, headers=h, json=j)
G = lambda h, p: httpx.get(BASE + p, headers=h)


def env(k):
    for l in open("/app/backend/.env"):
        if l.startswith(k + "="): return l.split("=", 1)[1].strip().strip('"')


DB = MongoClient(env("MONGO_URL"))[env("DB_NAME")]


def member(h, mid):
    return [m for m in G(h, "/allocation").json()["members"] if m["id"] == mid][0]


def eng(h):
    return [d for d in G(h, "/allocation").json()["departments"] if d["id"] == "dep_engineering"][0]


def test_admin_view_and_over_budget_errors():
    a = demo("admin"); d = G(a, "/allocation").json()
    assert len(d["departments"]) == 4 and d["org"]["budget"] == 50000
    assert all("health" in m for m in d["members"])
    assert any(x["health"] == "underutilised" for x in d["departments"] + d["members"])
    r = PUT(a, "/allocation/org", {"credits": 1}); assert r.status_code == 400 and "Department budgets exceed organisation budget" in r.text
    r = PUT(a, "/allocation/departments/dep_engineering", {"credits": 1}); assert "Allocations exceed department budget" in r.text
    r = PUT(a, "/allocation/departments/dep_engineering", {"credits": 999999}); assert "Department budgets exceed organisation budget" in r.text
    r = PUT(a, "/allocation/members/usr_arjun_mehta", {"credits": 999999}); assert r.status_code == 400 and "Allocations exceed department budget" in r.text
    assert G(a, "/allocation").json()["org"]["budget"] == 50000


def test_manager_reallocate_and_limits():
    s = demo("manager")
    ms = [m for m in G(s, "/allocation").json()["members"] if m["department_id"] == "dep_engineering"]
    assert {m["department_id"] for m in G(s, "/allocation").json()["members"]} == {"dep_engineering"}
    src = max(ms, key=lambda m: m["unused"]); dst = [m for m in ms if m["id"] != src["id"]][0]
    r = P(s, "/allocation/reallocate", {"from_user_id": src["id"], "to_user_id": dst["id"], "credits": 10}); assert r.status_code == 200, r.text
    assert member(s, src["id"])["allocation"] == src["allocation"] - 10
    assert member(s, dst["id"])["allocation"] == dst["allocation"] + 10
    # restore
    assert P(s, "/allocation/reallocate", {"from_user_id": dst["id"], "to_user_id": src["id"], "credits": 10}).status_code == 200
    r = P(s, "/allocation/reallocate", {"from_user_id": src["id"], "to_user_id": "usr_aisha_bello", "credits": 1}); assert r.status_code == 403
    r = P(s, "/allocation/reallocate", {"from_user_id": src["id"], "to_user_id": dst["id"], "credits": src["unused"] + 1})
    assert r.status_code == 400 and "unused allocation" in r.text
    assert member(s, src["id"])["allocation"] == src["allocation"]


def test_requests_approve_reject_cancel_records():
    e, s, a = demo("employee"), demo("manager"), demo("admin")
    tag = f"tscheck-req-{uuid.uuid4().hex[:6]}"
    # validation
    r = P(e, "/allocation/requests", {"amount": 0, "reason": " ", "urgency": "high"})
    assert r.status_code == 422 and {"amount", "reason"} <= set(r.json()["detail"]["fields"])
    assert P(s, "/allocation/requests", {"amount": 5, "reason": tag, "urgency": "low"}).status_code == 403
    rq = P(e, "/allocation/requests", {"amount": 500, "reason": tag, "urgency": "high"}).json()
    assert rq["status"] == "pending" and rq["urgency"] == "high"
    for h in (s, a): assert rq["id"] in [x["id"] for x in G(h, "/allocation/requests").json()]
    assert {x["requester_id"] for x in G(e, "/allocation/requests").json()} == {"usr_arjun_mehta"}
    ev = G(e, "/allocation").json(); assert "members" not in ev and "departments" not in ev and ev["me"]["id"] == "usr_arjun_mehta"
    # employee cannot approve / allocate
    assert P(e, f"/allocation/requests/{rq['id']}/approve", {"credits": 1}).status_code == 403
    assert PUT(e, "/allocation/members/usr_arjun_mehta", {"credits": 1}).status_code == 403
    before, pool = member(a, "usr_arjun_mehta")["allocation"], eng(a)["unallocated"]
    r = P(s, f"/allocation/requests/{rq['id']}/approve", {"credits": 300}); assert r.status_code == 200, r.text
    try:
        assert r.json()["approved_credits"] == 300
        assert member(a, "usr_arjun_mehta")["allocation"] == before + 300
        assert eng(a)["unallocated"] == pool - 300
    finally:  # restore seeded allocation
        assert PUT(a, "/allocation/members/usr_arjun_mehta", {"credits": before}).status_code == 200
    big = P(e, "/allocation/requests", {"amount": 50000, "reason": tag, "urgency": "normal"}).json()
    r = P(s, f"/allocation/requests/{big['id']}/approve", {"credits": 50000})
    assert r.status_code == 400 and "Not enough unallocated department budget" in r.text
    r = P(s, f"/allocation/requests/{big['id']}/reject", {"note": tag + " note"}); assert r.status_code == 200
    mine = [x for x in G(e, "/allocation/requests").json() if x["id"] == big["id"]][0]
    assert mine["status"] == "rejected" and tag in str(mine)
    c = P(e, "/allocation/requests", {"amount": 5, "reason": tag, "urgency": "low"}).json()
    assert P(e, f"/allocation/requests/{c['id']}/cancel").status_code == 200
    assert [x for x in G(e, "/allocation/requests").json() if x["id"] == c["id"]][0]["status"] == "cancelled"
    # records
    for rid, act in ((rq["id"], "approved"), (big["id"], "rejected"), (c["id"], "cancelled"), (rq["id"], "created")):
        assert DB.audit_log.find_one({"action": f"allocation.request.{act}", "meta.request_id": rid}) or \
               DB.audit_log.find_one({"action": f"allocation.request.{act}", "metadata.request_id": rid}) or \
               DB.audit_log.find_one({"action": f"allocation.request.{act}", "$where": f"JSON.stringify(this).includes('{rid}')"}), (rid, act)
    assert DB.notifications.find_one({"user_id": "usr_arjun_mehta", "type": "allocation.request.approved"})
    assert DB.notifications.find_one({"user_id": "usr_sofia_marchetti", "type": "allocation.request"})


def test_reconcile_exits_zero():
    p = subprocess.run([__import__("sys").executable, "scripts/reconcile.py"], cwd=__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-800:]
