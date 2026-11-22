# Phase 2: Credit Lending (JRN-19..35) + Resource Allocation (JRN-36..50), Q-8 concurrency, Q-9 RBAC
import os
import uuid
import concurrent.futures as cf
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
DISCLAIMER = "Obligation tracking only. No provider credits are transferred."
CREATED_USERS, CREATED_ENTRIES, CREATED_REQUESTS = [], [], []
RESTORE_ALLOC = {}   # user_id -> original credits
T0 = None


def _mongo():
    env = {}
    with open("/app/backend/.env") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"')
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


def tok(key):
    r = requests.post(f"{API}/demo/login", json={"key": key})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register(name):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": name, "email": email, "password": "Passw0rd!x",
                                                     "mode": "individual", "org_name": ""})
    assert r.status_code == 200, r.text
    d = r.json()
    CREATED_USERS.append(d["user"]["id"])
    return {"id": d["user"]["id"], "email": email, "h": {"Authorization": f"Bearer {d['access_token']}"}}


@pytest.fixture(scope="module")
def T():
    return {k: tok(k) for k in ["admin", "manager", "employee", "individual", "tomas", "hana", "kwame"]}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    global T0
    db = _mongo()
    T0 = db.audit_log.count_documents({})
    yield
    # restore allocations first (via API as admin so audit is consistent), then delete created data by id
    h = tok("admin")
    for uid, credits in sorted(RESTORE_ALLOC.items(), key=lambda kv: kv[1]):
        requests.put(f"{API}/allocation/members/{uid}", json={"credits": credits}, headers=h)
    for uid, credits in RESTORE_ALLOC.items():
        requests.put(f"{API}/allocation/members/{uid}", json={"credits": credits}, headers=h)
    for rid in CREATED_REQUESTS:
        db.resource_requests.delete_one({"id": rid})
        db.notifications.delete_many({"meta.request_id": rid})
    for eid in CREATED_ENTRIES:
        db.lending_ledger.delete_one({"id": eid})
        db.lending_repayments.delete_many({"loan_id": eid})
        db.notifications.delete_many({"meta.entry_id": eid})
    for uid in CREATED_USERS:
        db.friendships.delete_many({"$or": [{"requester_id": uid}, {"addressee_id": uid}]})
        for e in db.lending_ledger.find({"$or": [{"lender_id": uid}, {"borrower_id": uid}]}, {"id": 1}):
            db.lending_repayments.delete_many({"loan_id": e["id"]})
            db.notifications.delete_many({"meta.entry_id": e["id"]})
        db.lending_ledger.delete_many({"$or": [{"lender_id": uid}, {"borrower_id": uid}]})
        db.notifications.delete_many({"user_id": uid})
        db.allocations.delete_many({"scope_type": "user", "scope_id": uid})
        db.audit_log.delete_many({"actor_id": uid})
        db.users.delete_one({"id": uid, "is_demo": False})


def summ(h):
    return requests.get(f"{API}/lending/summary", headers=h).json()


def create(h, kind, friend_id, amount, reason="TEST_reason", due=None):
    r = requests.post(f"{API}/lending/{kind}", json={"friend_id": friend_id, "amount": amount, "reason": reason, "due_date": due}, headers=h)
    if r.status_code == 200:
        CREATED_ENTRIES.append(r.json()["id"])
    return r


def act(h, eid, action):
    return requests.post(f"{API}/lending/entries/{eid}/{action}", headers=h)


class TestLending:
    S = {}

    def test_jrn19_maya_page_data(self, T):
        d = requests.get(f"{API}/lending/entries", headers=T["individual"]).json()
        assert d["disclaimer"] == DISCLAIMER
        by = {e["id"]: e for e in d["entries"]}
        assert {"lnd_001", "lnd_002", "lnd_003", "lnd_004"} <= set(by)
        assert by["lnd_001"]["overdue"] is True  # JRN-34
        assert by["lnd_004"]["needs_my_action"] is True and by["lnd_004"]["actions"]["accept"] is True
        for tab in ["borrowed", "lent", "pending"]:
            r = requests.get(f"{API}/lending/entries", params={"tab": tab}, headers=T["individual"])
            assert r.status_code == 200
        s = summ(T["individual"])
        assert s["simulated_disclaimer"] == DISCLAIMER and s["pending_actions"] >= 1
        assert requests.get(f"{API}/lending/entries/lnd_001", headers=T["individual"]).json()["disclaimer"] == DISCLAIMER

    def test_jrn20_add_friend_and_accept(self, T):
        a = register("TEST_FriendA")
        b = register("TEST_Outsider")
        self.S.update(a=a, b=b)
        r = requests.post(f"{API}/friends/requests", json={"email": a["email"].upper()}, headers=T["individual"])
        assert r.status_code == 200, r.text
        inc = requests.get(f"{API}/friends", headers=a["h"]).json()["incoming"]
        assert len(inc) == 1 and inc[0]["user"]["id"] == "usr_maya_ellison"
        r = requests.post(f"{API}/friends/requests", json={"email": a["email"]}, headers=T["individual"])
        assert r.status_code == 409
        r = requests.post(f"{API}/friends/requests/{inc[0]['id']}/accept", headers=a["h"])
        assert r.status_code == 200
        assert any(f["user"]["id"] == "usr_maya_ellison" for f in r.json()["friends"])
        assert requests.post(f"{API}/friends/requests/{inc[0]['id']}/accept", headers=a["h"]).status_code == 409
        mf = requests.get(f"{API}/friends", headers=T["individual"]).json()["friends"]
        assert any(f["user"]["id"] == a["id"] for f in mf)

    def test_jrn21_unknown_and_org_email(self, T):
        for email in ["arjun.mehta@nexora.io", f"nobody_{uuid.uuid4().hex[:6]}@example.com"]:
            r = requests.post(f"{API}/friends/requests", json={"email": email}, headers=T["individual"])
            assert r.status_code == 404
            assert r.json()["detail"]["message"] == "No individual user found with that email"

    def test_jrn25_invalid_amounts(self, T):
        a = self.S["a"]
        before = len(requests.get(f"{API}/lending/entries", headers=T["individual"]).json()["entries"])
        for amt in [0, -5, 2.5, "abc", None]:
            r = create(T["individual"], "requests", a["id"], amt)
            assert r.status_code == 422, (amt, r.text)
            assert "amount" in r.json()["detail"]["fields"]
        r = create(T["individual"], "requests", a["id"], 10, reason="  ")
        assert r.status_code == 422 and "reason" in r.json()["detail"]["fields"]
        r = create(T["individual"], "requests", "usr_tomas_reyes_x", 10)
        assert r.status_code == 422 and "friend_id" in r.json()["detail"]["fields"]
        r = create(T["individual"], "requests", a["id"], 10, due="2020-01-01")
        assert r.status_code == 422
        assert len(requests.get(f"{API}/lending/entries", headers=T["individual"]).json()["entries"]) == before

    def test_jrn22_23_request_accept(self, T):
        a = self.S["a"]
        m0, a0 = summ(T["individual"]), summ(a["h"])
        r = create(T["individual"], "requests", a["id"], 100, reason="TEST_need capacity")
        assert r.status_code == 200, r.text
        e = r.json()
        assert e["status"] == "pending" and e["direction"] == "borrowed" and e["disclaimer"] == DISCLAIMER
        self.S["loan"] = e["id"]
        assert summ(T["individual"])["available"] == m0["available"]
        ae = requests.get(f"{API}/lending/entries/{e['id']}", headers=a["h"]).json()
        assert ae["needs_my_action"] and ae["actions"]["accept"]
        assert act(T["individual"], e["id"], "accept").status_code == 403  # initiator can't accept
        r = act(a["h"], e["id"], "accept")
        assert r.status_code == 200 and r.json()["status"] == "active"
        m1, a1 = summ(T["individual"]), summ(a["h"])
        assert m1["available"] == m0["available"] + 100 and m1["borrowed_outstanding"] == m0["borrowed_outstanding"] + 100
        assert a1["available"] == a0["available"] - 100 and a1["lent_outstanding"] == 100
        ov = requests.get(f"{API}/overview", params={"days": 30}, headers=T["individual"]).json()
        assert ov["lending"]["available"] == m1["available"]  # REQ-41 overview panel
        assert act(a["h"], e["id"], "accept").status_code == 409

    def test_jrn28_29_30_repay_flow(self, T):
        a, eid = self.S["a"], self.S["loan"]
        r = requests.post(f"{API}/lending/entries/{eid}/repayments", json={"amount": 40}, headers=T["individual"])
        assert r.status_code == 200, r.text
        rep = [x for x in r.json()["repayments"] if x["status"] == "awaiting_confirmation"][0]
        assert requests.post(f"{API}/lending/repayments/{rep['id']}/confirm", headers=T["individual"]).status_code == 403
        r = requests.post(f"{API}/lending/repayments/{rep['id']}/confirm", headers=a["h"])
        assert r.status_code == 200
        d = r.json()
        assert d["outstanding"] == 60 and d["status"] == "active"
        assert any(h["action"] == "repayment_confirmed" for h in d["history"])
        assert requests.post(f"{API}/lending/repayments/{rep['id']}/confirm", headers=a["h"]).status_code == 409
        r = requests.post(f"{API}/lending/entries/{eid}/repayments", json={"amount": 80}, headers=T["individual"])
        assert r.status_code == 400 and r.json()["detail"]["fields"]["amount"] == "Repayment exceeds outstanding amount"
        r = requests.post(f"{API}/lending/entries/{eid}/repayments", json={"amount": 60}, headers=T["individual"])
        assert r.status_code == 200
        rep2 = [x for x in r.json()["repayments"] if x["status"] == "awaiting_confirmation"][0]
        # lender can't record repayment
        assert requests.post(f"{API}/lending/entries/{eid}/repayments", json={"amount": 1}, headers=a["h"]).status_code == 403
        d = requests.post(f"{API}/lending/repayments/{rep2['id']}/confirm", headers=a["h"]).json()
        assert d["status"] == "repaid" and d["outstanding"] == 0

    def test_jrn31_dispute(self, T):
        a = self.S["a"]
        e = create(T["individual"], "requests", a["id"], 50, reason="TEST_dispute").json()
        act(a["h"], e["id"], "accept")
        d = requests.post(f"{API}/lending/entries/{e['id']}/repayments", json={"amount": 20}, headers=T["individual"]).json()
        rid = d["repayments"][0]["id"]
        d = requests.post(f"{API}/lending/repayments/{rid}/dispute", headers=a["h"]).json()
        assert d["repayments"][0]["status"] == "disputed" and d["outstanding"] == 50 and d["status"] == "active"
        # seeded rep_003 is confirmable by Hana (read-only check)
        h = requests.get(f"{API}/lending/entries/lnd_002", headers=T["hana"]).json()
        assert any(r["id"] == "rep_003" and r["can_confirm"] for r in h["repayments"])

    def test_jrn26_offer_decline_and_27_cancel(self, T):
        a = self.S["a"]
        m0 = summ(T["individual"])
        e = create(T["individual"], "offers", a["id"], 30, reason="").json()
        assert e["status"] == "pending" and e["direction"] == "lent"
        assert act(a["h"], e["id"], "decline").json()["status"] == "declined"
        assert summ(T["individual"])["available"] == m0["available"]
        e2 = create(T["individual"], "requests", a["id"], 25).json()
        assert act(a["h"], e2["id"], "cancel").status_code == 403
        assert act(T["individual"], e2["id"], "cancel").json()["status"] == "cancelled"
        assert act(T["individual"], e2["id"], "cancel").status_code == 409
        r = create(T["individual"], "offers", a["id"], 10 ** 7)
        assert r.status_code == 400 and r.json()["detail"]["fields"]["amount"] == "Not enough available credits to lend"

    def test_jrn24_kwame_not_enough(self, T):
        k = summ(T["kwame"])
        e = create(T["individual"], "requests", "usr_kwame_boateng", max(500, k["available"] + 50)).json()
        r = act(T["kwame"], e["id"], "accept")
        assert r.status_code == 400 and r.json()["detail"] == "Not enough available credits to lend"
        assert requests.get(f"{API}/lending/entries/{e['id']}", headers=T["individual"]).json()["status"] == "pending"
        act(T["individual"], e["id"], "cancel")

    def test_jrn32_q9_lending_rbac(self, T):
        b = self.S["b"]
        assert requests.get(f"{API}/lending/entries/lnd_001", headers=b["h"]).status_code == 403
        assert requests.get(f"{API}/lending/entries/{self.S['loan']}", headers=b["h"]).status_code == 403
        assert act(b["h"], "lnd_004", "accept").status_code == 403
        assert requests.get(f"{API}/lending/entries/lnd_001", headers=T["hana"]).status_code == 403
        for k in ["admin", "manager", "employee"]:
            for path in ["/lending/summary", "/lending/entries", "/lending/entries/lnd_001", "/friends"]:
                assert requests.get(f"{API}{path}", headers=T[k]).status_code == 403, (k, path)
            assert requests.post(f"{API}/friends/requests", json={"email": "x@y.z"}, headers=T[k]).status_code == 403
            assert requests.post(f"{API}/lending/requests", json={}, headers=T[k]).status_code == 403
            assert requests.post(f"{API}/lending/entries/lnd_004/accept", headers=T[k]).status_code == 403

    def test_q8_parallel_accept_5_trials(self, T):
        a = self.S["a"]
        for i in range(5):
            e = create(T["individual"], "requests", a["id"], 10, reason=f"TEST_race{i}").json()
            before = summ(a["h"])["available"]
            with cf.ThreadPoolExecutor(2) as ex:
                codes = sorted(ex.map(lambda _: act(a["h"], e["id"], "accept").status_code, range(2)))
            assert codes == [200, 409], codes
            assert summ(a["h"])["available"] == before - 10
            hist = requests.get(f"{API}/lending/entries/{e['id']}", headers=a["h"]).json()["history"]
            assert sum(1 for h in hist if h["action"] == "accepted") == 1


def alloc(h, days=30):
    return requests.get(f"{API}/allocation", params={"days": days}, headers=h).json()


def remember(uid, credits):
    RESTORE_ALLOC.setdefault(uid, credits)


class TestAllocation:
    S = {}

    def test_jrn36_admin_view(self, T):
        d = alloc(T["admin"])
        assert d["org"]["budget"] == 50000 and d["org"]["departments_total"] == 46000
        eng = [x for x in d["departments"] if x["id"] == "dep_engineering"][0]
        assert eng["budget"] == 20000 and eng["allocated"] == 19000 and eng["unallocated"] == 1000
        m = d["members"][0]
        for k in ["allocation", "monthly_allocation", "credits", "remaining", "utilisation", "health"]:
            assert k in m, k
        assert isinstance(d["suggestions"], list)
        self.S["members"] = {x["id"]: x for x in d["members"]}
        for x in d["members"]:
            remember(x["id"], x["monthly_allocation"])

    def test_jrn37_dept_exceeds_org(self, T):
        r = requests.put(f"{API}/allocation/departments/dep_engineering", json={"credits": 24001}, headers=T["admin"])
        assert r.status_code == 400 and r.json()["detail"]["fields"]["credits"] == "Department budgets exceed organisation budget"
        r = requests.put(f"{API}/allocation/org", json={"credits": 45999}, headers=T["admin"])
        assert r.status_code == 400
        r = requests.put(f"{API}/allocation/departments/dep_engineering", json={"credits": 18999}, headers=T["admin"])
        assert r.status_code == 400 and r.json()["detail"]["fields"]["credits"] == "Allocations exceed department budget"
        assert requests.put(f"{API}/allocation/departments/dep_engineering", json={"credits": 20000}, headers=T["manager"]).status_code == 403
        assert alloc(T["admin"])["org"]["departments_total"] == 46000

    def test_jrn38_member_exceeds_dept(self, T):
        r = requests.put(f"{API}/allocation/members/usr_arjun_mehta", json={"credits": 999999}, headers=T["manager"])
        assert r.status_code == 400 and r.json()["detail"]["fields"]["credits"] == "Allocations exceed department budget"
        r = requests.put(f"{API}/allocation/members/usr_arjun_mehta", json={"credits": -1}, headers=T["manager"])
        assert r.status_code == 422

    def test_jrn39_40_reallocate(self, T):
        d = alloc(T["manager"])
        assert all(m["department_id"] == "dep_engineering" for m in d["members"])
        sug = d["suggestions"]
        assert sug, "no suggestions for Engineering"
        s = sug[0]
        members = {m["id"]: m for m in d["members"]}
        src, dst = members[s["from_user_id"]], members[s["to_user_id"]]
        n = 200 if src["unused"] >= 200 else s["credits"]
        r = requests.post(f"{API}/allocation/reallocate", json={"from_user_id": src["id"], "to_user_id": dst["id"], "credits": n}, headers=T["manager"])
        assert r.status_code == 200, r.text
        after = {m["id"]: m for m in alloc(T["manager"])["members"]}
        assert after[src["id"]]["monthly_allocation"] == src["monthly_allocation"] - n
        assert after[dst["id"]]["monthly_allocation"] == dst["monthly_allocation"] + n
        self.S["src"] = src
        # JRN-40: too much / other dept
        r = requests.post(f"{API}/allocation/reallocate", json={"from_user_id": src["id"], "to_user_id": dst["id"], "credits": 10 ** 6}, headers=T["manager"])
        assert r.status_code == 400 and "unused allocation" in r.json()["detail"]["fields"]["credits"]
        mkt = [m for m in self.S["members"].values() if m["department_id"] == "dep_marketing"][0]
        self.S["mkt"] = mkt
        r = requests.post(f"{API}/allocation/reallocate", json={"from_user_id": src["id"], "to_user_id": mkt["id"], "credits": 10}, headers=T["manager"])
        assert r.status_code == 403
        r = requests.post(f"{API}/allocation/reallocate", json={"from_user_id": src["id"], "to_user_id": src["id"], "credits": 10}, headers=T["manager"])
        assert r.status_code == 400

    def test_jrn41_employee_view(self, T):
        d = alloc(T["employee"])
        assert d["me"]["id"] == "usr_arjun_mehta" and "members" not in d
        assert all(r["requester_id"] == "usr_arjun_mehta" for r in d["requests"])
        self.S["arjun_alloc"] = d["me"]["monthly_allocation"]

    def test_jrn42_43_44_45_requests(self, T):
        r = requests.post(f"{API}/allocation/requests", json={"amount": 0, "reason": "x", "urgency": "high"}, headers=T["employee"])
        assert r.status_code == 422 and "amount" in r.json()["detail"]["fields"]
        r = requests.post(f"{API}/allocation/requests", json={"amount": 10, "reason": " ", "urgency": "high"}, headers=T["employee"])
        assert r.status_code == 422 and "reason" in r.json()["detail"]["fields"]
        r = requests.post(f"{API}/allocation/requests", json={"amount": 500, "reason": "TEST_Release crunch", "urgency": "high"}, headers=T["employee"])
        assert r.status_code == 200, r.text
        rq = r.json()
        CREATED_REQUESTS.append(rq["id"])
        assert rq["status"] == "pending" and rq["urgency"] == "high"
        for k in ["manager", "admin"]:
            assert any(x["id"] == rq["id"] for x in alloc(T[k])["requests"]), k
        assert requests.post(f"{API}/allocation/requests", json={"amount": 5, "reason": "x"}, headers=T["manager"]).status_code == 403
        pool0 = [x for x in alloc(T["manager"])["departments"] if x["id"] == "dep_engineering"][0]["unallocated"]
        r = requests.post(f"{API}/allocation/requests/{rq['id']}/approve", json={"credits": 501}, headers=T["manager"])
        assert r.status_code == 400
        r = requests.post(f"{API}/allocation/requests/{rq['id']}/approve", json={"credits": 300}, headers=T["manager"])
        assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["approved_credits"] == 300
        pool1 = [x for x in alloc(T["manager"])["departments"] if x["id"] == "dep_engineering"][0]["unallocated"]
        assert pool1 == pool0 - 300
        assert alloc(T["employee"])["me"]["monthly_allocation"] == self.S["arjun_alloc"] + 300
        r = requests.post(f"{API}/allocation/requests/req_001/approve", json={}, headers=T["manager"])
        assert r.status_code == 400 and r.json()["detail"]["fields"]["credits"] == "Not enough unallocated department budget"

    def test_jrn46_47_reject_cancel(self, T):
        ids = []
        for _ in range(2):
            rq = requests.post(f"{API}/allocation/requests", json={"amount": 20, "reason": "TEST_r", "urgency": "low"}, headers=T["employee"]).json()
            CREATED_REQUESTS.append(rq["id"])
            ids.append(rq["id"])
        r = requests.post(f"{API}/allocation/requests/{ids[0]}/reject", json={"note": "TEST_not now"}, headers=T["manager"])
        assert r.status_code == 200
        mine = {x["id"]: x for x in alloc(T["employee"])["requests"]}
        assert mine[ids[0]]["status"] == "rejected" and mine[ids[0]]["decision_note"] == "TEST_not now"
        assert requests.post(f"{API}/allocation/requests/{ids[0]}/reject", json={"note": "x"}, headers=T["manager"]).status_code == 409
        assert requests.post(f"{API}/allocation/requests/{ids[1]}/cancel", headers=T["manager"]).status_code == 403
        r = requests.post(f"{API}/allocation/requests/{ids[1]}/cancel", headers=T["employee"])
        assert r.status_code == 200 and r.json()["status"] == "cancelled"

    def test_jrn48_q9_allocation_rbac(self, T):
        e = T["employee"]
        assert requests.put(f"{API}/allocation/members/usr_arjun_mehta", json={"credits": 1}, headers=e).status_code == 403
        assert requests.post(f"{API}/allocation/reallocate", json={}, headers=e).status_code == 403
        assert requests.post(f"{API}/allocation/requests/req_001/approve", json={}, headers=e).status_code == 403
        assert requests.post(f"{API}/allocation/requests/req_001/reject", json={}, headers=e).status_code == 403
        assert requests.put(f"{API}/allocation/org", json={"credits": 1}, headers=e).status_code == 403
        mkt = self.S["mkt"]
        assert requests.put(f"{API}/allocation/members/{mkt['id']}", json={"credits": 1}, headers=T["manager"]).status_code == 403
        assert requests.post(f"{API}/allocation/requests/req_002/approve", json={}, headers=T["manager"]).status_code == 403
        for k in ["individual", "tomas"]:
            assert requests.get(f"{API}/allocation", headers=T[k]).status_code == 403
            assert requests.get(f"{API}/allocation/requests", headers=T[k]).status_code == 403

    def test_q8_parallel_approve_5_trials(self, T):
        for i in range(5):
            rq = requests.post(f"{API}/allocation/requests", json={"amount": 10, "reason": f"TEST_race{i}", "urgency": "normal"}, headers=T["employee"]).json()
            CREATED_REQUESTS.append(rq["id"])
            before = alloc(T["employee"])["me"]["monthly_allocation"]
            hs = [T["manager"], T["admin"]]
            with cf.ThreadPoolExecutor(2) as ex:
                codes = sorted(ex.map(lambda h: requests.post(f"{API}/allocation/requests/{rq['id']}/approve", json={}, headers=h).status_code, hs))
            assert codes == [200, 409], codes
            assert alloc(T["employee"])["me"]["monthly_allocation"] == before + 10

    def test_jrn50_notifications_audit(self, T):
        db = _mongo()
        rid = CREATED_REQUESTS[0]
        assert db.notifications.find_one({"user_id": "usr_sofia_marchetti", "meta.request_id": rid})
        assert db.notifications.find_one({"user_id": "usr_daniel_okafor", "meta.request_id": rid})
        assert db.notifications.find_one({"user_id": "usr_arjun_mehta", "type": "allocation.request.approved", "meta.request_id": rid})
        for action in ["allocation.request.created", "allocation.request.approved", "allocation.request.rejected",
                       "allocation.request.cancelled", "allocation.reallocated"]:
            assert db.audit_log.find_one({"action": action}), action
        src = self.S["src"]
        assert db.notifications.find_one({"user_id": src["id"], "type": "allocation.reallocated"})
