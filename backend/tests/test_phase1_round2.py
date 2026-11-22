# Phase 1 review-fix round 2: lending ledger, usage filters + scoping, granularity, view-as perms, individual independence, google
import os
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
CREATED = []


def _mongo():
    env = {}
    with open("/app/backend/.env") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"')
    return MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    db = _mongo()
    for uid in CREATED:
        u = db.users.find_one({"id": uid})
        if u and u.get("org_id") and not u.get("is_demo"):
            db.organizations.delete_one({"id": u["org_id"], "owner_id": uid})
            db.allocations.delete_many({"scope_type": "org", "scope_id": u["org_id"]})
        db.allocations.delete_many({"scope_type": "user", "scope_id": uid})
        db.audit_log.delete_many({"actor_id": uid})
        db.users.delete_one({"id": uid, "is_demo": False})


def tok(key):
    r = requests.post(f"{API}/demo/login", json={"key": key})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def T():
    return {k: {"Authorization": f"Bearer {tok(k)}"} for k in ["admin", "manager", "employee", "individual"]}


def register_individual():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "TEST_Indie", "email": email, "password": "Passw0rd!",
                                                     "mode": "individual", "org_name": ""})
    assert r.status_code == 200, r.text
    CREATED.append(r.json()["user"]["id"])
    return r.json()


# Lending
class TestLending:
    def test_maya_summary(self, T):
        s = requests.get(f"{API}/lending/summary", headers=T["individual"]).json()
        assert s["lent_outstanding"] == 200 and s["borrowed_outstanding"] == 250
        assert s["net"] == -50 and s["pending_requests"] == 1
        assert s["simulated_disclaimer"] == "Obligation tracking only. No provider credits are transferred."

    def test_maya_ledger(self, T):
        d = requests.get(f"{API}/lending/ledger", headers=T["individual"]).json()
        ids = sorted(e["id"] for e in d["entries"])
        assert ids == ["lnd_001", "lnd_002", "lnd_003", "lnd_004"]
        by = {e["id"]: e for e in d["entries"]}
        assert by["lnd_001"]["outstanding"] == 200 and by["lnd_001"]["direction"] == "lent"
        assert by["lnd_002"]["direction"] == "borrowed"

    def test_lending_forbidden_for_org_roles(self, T):
        for k in ["admin", "manager", "employee"]:
            assert requests.get(f"{API}/lending/ledger", headers=T[k]).status_code == 403

    def test_new_individual_empty(self):
        d = register_individual()
        h = {"Authorization": f"Bearer {d['access_token']}"}
        assert d["user"]["organization"] is None and d["user"]["department"] is None
        assert "lending" in d["user"]["allowed_modules"]
        assert requests.get(f"{API}/lending/ledger", headers=h).json()["entries"] == []
        s = requests.get(f"{API}/lending/summary", headers=h).json()
        assert s["net"] == 0 and s["pending_requests"] == 0
        u = requests.get(f"{API}/usage", headers=h).json()
        assert u["totals"]["credits"] == 0 and u["scope"]["label"] == "Your usage"
        ov = requests.get(f"{API}/overview", headers=h).text
        assert "Nexora" not in ov and "Engineering" not in ov


# Usage
class TestUsage:
    @pytest.mark.parametrize("key", ["admin", "manager", "employee", "individual"])
    def test_granularity_and_metrics(self, T, key):
        for days, gran, n in [(7, "day", 7), (30, "day", 30), (90, "week", 13)]:
            u = requests.get(f"{API}/usage", params={"days": days}, headers=T[key]).json()
            assert u["granularity"] == gran and len(u["timeseries"]) == n
            t = u["totals"]
            assert t["avg_per_day"] == round(t["credits"] / days)
            assert "change_pct" in t
            assert abs(sum(p["share"] for p in u["providers"]) - 100) < 1 or t["credits"] == 0

    def test_scope_labels(self, T):
        lab = {k: requests.get(f"{API}/usage", headers=T[k]).json()["scope"]["label"] for k in T}
        assert lab["admin"] == "Nexora Technologies"
        assert lab["manager"] == "Engineering department"
        assert lab["employee"] == "Your usage" and lab["individual"] == "Your usage"

    def test_individual_no_nexora(self, T):
        for p in ["/usage?days=30", "/usage?days=90", "/overview?days=30", "/lending/ledger", "/lending/summary", "/auth/me"]:
            txt = requests.get(f"{API}{p}", headers=T["individual"]).text
            assert "Nexora" not in txt and "dep_" not in txt and "org_" not in txt.replace('"org_id":null', ""), p

    def test_filters(self, T):
        base = requests.get(f"{API}/usage", headers=T["admin"]).json()
        c = requests.get(f"{API}/usage", params={"provider": "claude"}, headers=T["admin"]).json()
        assert c["totals"]["credits"] == next(p["credits"] for p in base["providers"] if p["id"] == "claude")
        d = requests.get(f"{API}/usage", params={"department_id": "dep_engineering"}, headers=T["admin"]).json()
        mgr = requests.get(f"{API}/usage", headers=T["manager"]).json()
        assert d["totals"]["credits"] == mgr["totals"]["credits"]
        assert all(m["department"] == "Engineering" for m in d["members"])
        m = requests.get(f"{API}/usage", params={"member_id": "usr_ravi_iyer"}, headers=T["admin"]).json()
        m2 = requests.get(f"{API}/usage", params={"member_id": "usr_ravi_iyer"}, headers=T["manager"]).json()
        assert m["totals"]["credits"] == m2["totals"]["credits"]
        assert len(m["members"]) == 1 and m["members"][0]["id"] == "usr_ravi_iyer"
        assert m["departments"] is None
        assert base["filter_options"]["departments"] and base["filter_options"]["members"]
        assert mgr["filter_options"]["departments"] == []
        assert requests.get(f"{API}/usage", headers=T["employee"]).json()["filter_options"] == {"departments": [], "members": []}

    def test_filter_scoping(self, T):
        g = lambda k, **p: requests.get(f"{API}/usage", params=p, headers=T[k]).status_code
        assert g("employee", member_id="usr_arjun_mehta") == 403
        assert g("individual", member_id="usr_maya_ellison") == 403
        assert g("employee", department_id="dep_engineering") == 403
        assert g("manager", member_id="usr_oliver_grant") == 403
        assert g("manager", department_id="dep_engineering") == 403
        assert g("admin", department_id="dep_unknown") == 403
        assert g("admin", member_id="usr_maya_ellison") == 403
        assert g("admin", provider="nope") == 400
        assert g("employee", provider="claude") == 200


# View as
class TestViewAs:
    def test_switch_admin_to_employee_cookie_perms(self):
        s = requests.Session()
        assert s.post(f"{API}/demo/login", json={"key": "admin"}).status_code == 200
        assert s.get(f"{API}/team/members").status_code == 200
        r = s.post(f"{API}/demo/switch", json={"target_user_id": "usr_arjun_mehta"})
        assert r.status_code == 200 and r.json()["user"]["role"] == "employee"
        assert s.get(f"{API}/auth/me").json()["id"] == "usr_arjun_mehta"
        assert s.get(f"{API}/team/members").status_code == 403
        assert s.get(f"{API}/usage").json()["scope"]["label"] == "Your usage"
        r = s.post(f"{API}/demo/switch", json={"target_user_id": "usr_maya_ellison"})
        assert s.get(f"{API}/lending/ledger").status_code == 200
        assert s.get(f"{API}/org").status_code == 403
        s.post(f"{API}/demo/switch", json={"target_user_id": "usr_sofia_marchetti"})
        assert s.get(f"{API}/usage").json()["scope"]["label"] == "Engineering department"


# Google
class TestGoogle:
    def test_fake_session(self):
        r = requests.post(f"{API}/auth/google/session", json={"session_id": "fake_" + uuid.uuid4().hex})
        # Orqestra: Emergent-managed Google sign-in is disabled unless ENABLE_EMERGENT_GOOGLE_AUTH=true
        assert r.status_code in (401, 503)

    def test_pending_complete_and_reuse(self):
        db = _mongo()
        token = "TEST_" + uuid.uuid4().hex
        email = f"test_g_{uuid.uuid4().hex[:6]}@example.com"
        db.pending_google_signups.insert_one({"token": token, "email": email, "name": "TEST_Google",
                                              "picture": None, "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
        r = requests.post(f"{API}/auth/google/complete", json={"pending_token": token, "mode": "individual", "org_name": ""})
        assert r.status_code == 200, r.text
        CREATED.append(r.json()["user"]["id"])
        assert r.json()["user"]["auth_provider"] == "google" if "auth_provider" in r.json()["user"] else True
        r2 = requests.post(f"{API}/auth/google/complete", json={"pending_token": token, "mode": "individual", "org_name": ""})
        assert r2.status_code == 401
        exp = "TEST_" + uuid.uuid4().hex
        db.pending_google_signups.insert_one({"token": exp, "email": "x_" + email, "name": "TEST_G",
                                              "expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)})
        r3 = requests.post(f"{API}/auth/google/complete", json={"pending_token": exp, "mode": "individual", "org_name": ""})
        db.pending_google_signups.delete_one({"token": exp})
        assert r3.status_code == 401
