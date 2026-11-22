# Phase 1 API regression: auth, demo login/switch, RBAC matrix, overview/usage data integrity, openapi
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
DEMO_PASSWORD = "Demo@12345"
DEMO_KEYS = ["admin", "manager", "employee", "individual"]
DEMO_IDS = {"admin": "usr_daniel_okafor", "manager": "usr_sofia_marchetti",
            "employee": "usr_arjun_mehta", "individual": "usr_maya_ellison"}

CREATED_USER_IDS = []


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
    if CREATED_USER_IDS:
        db = _mongo()
        for uid in CREATED_USER_IDS:
            u = db.users.find_one({"id": uid})
            if u and u.get("org_id") and not u.get("is_demo"):
                db.organizations.delete_one({"id": u["org_id"], "owner_id": uid})
                db.allocations.delete_many({"scope_type": "org", "scope_id": u["org_id"]})
            db.allocations.delete_many({"scope_type": "user", "scope_id": uid})
            db.audit_log.delete_many({"actor_id": uid})
            db.users.delete_one({"id": uid, "is_demo": False})


def demo_token(key):
    r = requests.post(f"{API}/demo/login", json={"key": key})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def tokens():
    return {k: demo_token(k) for k in DEMO_KEYS}


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def register(mode="individual", password="Passw0rd!", email=None, org_name=""):
    email = email or f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "TEST_User", "email": email, "password": password,
                                                     "mode": mode, "org_name": org_name})
    if r.status_code == 200:
        CREATED_USER_IDS.append(r.json()["user"]["id"])
    return r, email


# Auth
class TestAuth:
    def test_password_login_cookies_and_me(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": "daniel.okafor@nexora.io", "password": DEMO_PASSWORD})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"
        sc = r.headers.get("set-cookie", "")
        assert "access_token" in sc and "refresh_token" in sc and "HttpOnly" in sc
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200 and me.json()["email"] == "daniel.okafor@nexora.io"

    def test_wrong_password_random_email(self):
        r = requests.post(f"{API}/auth/login", json={"email": f"nobody_{uuid.uuid4().hex[:6]}@x.com", "password": "bad"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid email or password"

    def test_lockout_after_5(self):
        email = f"lock_{uuid.uuid4().hex[:6]}@x.com"
        codes = [requests.post(f"{API}/auth/login", json={"email": email, "password": "x"}).status_code for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429

    def test_register_individual_and_bcrypt(self):
        r, email = register()
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["mode"] == "individual" and u["role"] == "individual" and u["is_demo"] is False
        assert "team" not in u["allowed_modules"] and "allocation" not in u["allowed_modules"]
        doc = _mongo().users.find_one({"email": email})
        assert doc["password_hash"].startswith("$2b$")

    def test_register_org_admin(self):
        r, _ = register(mode="organisation", org_name="TEST_Org")
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["role"] == "admin" and u["organization"]["name"] == "TEST_Org"

    def test_register_duplicate_and_short_password(self):
        r, _ = register(email="daniel.okafor@nexora.io")
        assert r.status_code == 409 and "email" in r.json()["detail"]["fields"]
        email = f"short_{uuid.uuid4().hex[:6]}@example.com"
        r2, _ = register(password="12345", email=email)
        assert r2.status_code == 422 and "password" in r2.json()["detail"]["fields"]
        assert _mongo().users.find_one({"email": email}) is None

    def test_register_org_without_name(self):
        r, _ = register(mode="organisation", org_name="")
        assert r.status_code == 422 and "org_name" in r.json()["detail"]["fields"]

    def test_unauthenticated(self):
        assert requests.get(f"{API}/overview").status_code == 401
        assert requests.get(f"{API}/auth/me").status_code == 401


# Demo switch security
class TestDemoSwitch:
    def test_accounts(self):
        r = requests.get(f"{API}/demo/accounts")
        assert r.status_code == 200 and [a["key"] for a in r.json()] == DEMO_KEYS

    def test_demo_to_demo(self, tokens):
        r = requests.post(f"{API}/demo/switch", json={"target_user_id": DEMO_IDS["manager"]}, headers=h(tokens["admin"]))
        assert r.status_code == 200 and r.json()["user"]["role"] == "manager"

    def test_demo_to_non_demo(self, tokens):
        r = requests.post(f"{API}/demo/switch", json={"target_user_id": "usr_chloe_martin"}, headers=h(tokens["admin"]))
        assert r.status_code == 403

    def test_non_demo_user(self):
        r, _ = register()
        tok = r.json()["access_token"]
        r2 = requests.post(f"{API}/demo/switch", json={"target_user_id": DEMO_IDS["admin"]}, headers=h(tok))
        assert r2.status_code == 403


# RBAC matrix
EXPECTED = {
    "overview":        {"admin": 200, "manager": 200, "employee": 200, "individual": 200},
    "usage":           {"admin": 200, "manager": 200, "employee": 200, "individual": 200},
    "org":             {"admin": 200, "manager": 200, "employee": 200, "individual": 403},
    "org/departments": {"admin": 200, "manager": 200, "employee": 403, "individual": 403},
    "team/members":    {"admin": 200, "manager": 200, "employee": 403, "individual": 403},
    "lending/summary": {"admin": 403, "manager": 403, "employee": 403, "individual": 200},
    "lending/ledger":  {"admin": 403, "manager": 403, "employee": 403, "individual": 200},
}


class TestRBAC:
    @pytest.mark.parametrize("path", list(EXPECTED))
    def test_matrix(self, tokens, path):
        got = {k: requests.get(f"{API}/{path}", headers=h(tokens[k])).status_code for k in DEMO_KEYS}
        assert got == EXPECTED[path], f"{path}: {got}"

    def test_allowed_modules(self, tokens):
        mods = {k: requests.get(f"{API}/auth/me", headers=h(tokens[k])).json()["allowed_modules"] for k in DEMO_KEYS}
        assert len(mods["admin"]) == 11 and "lending" not in mods["admin"] and "tasks" in mods["admin"]  # Orqestra adds Tasks
        assert "lending" not in mods["manager"] and "integrations" not in mods["manager"]
        assert mods["employee"] == ["overview", "tasks", "usage", "allocation", "handover", "planner", "notifications", "settings"]
        assert "lending" in mods["individual"] and "team" not in mods["individual"] and "allocation" not in mods["individual"]


# Data integrity
class TestData:
    def test_admin_overview_matches_usage(self, tokens):
        for d in (7, 30, 90):
            ov = requests.get(f"{API}/overview?days={d}", headers=h(tokens["admin"])).json()
            us = requests.get(f"{API}/usage?days={d}", headers=h(tokens["admin"])).json()
            assert ov["cycle"]["used"] == us["totals"]["credits"]
            assert ov["cycle"]["budget"] == round(50000 * d / 30)
            assert sum(p["credits"] for p in us["providers"]) == us["totals"]["credits"]
            assert len(us["timeseries"]) == (13 if d == 90 else d)  # 90d is bucketed weekly since round 2
        assert ov["organization"]["name"] == "Nexora Technologies"
        assert ov["organization"]["employees"] == 12 and ov["organization"]["departments"] == 4

    def test_ranges_differ(self, tokens):
        t = [requests.get(f"{API}/usage?days={d}", headers=h(tokens["admin"])).json()["totals"]["credits"] for d in (7, 30, 90)]
        assert t[0] < t[1] < t[2]

    def test_invalid_days(self, tokens):
        assert requests.get(f"{API}/usage?days=14", headers=h(tokens["admin"])).status_code == 400

    def test_employee_self_only(self, tokens):
        us = requests.get(f"{API}/usage", headers=h(tokens["employee"])).json()
        assert us["scope"]["type"] == "self" and us["members"] is None and us["departments"] is None

    def test_manager_engineering(self, tokens):
        ov = requests.get(f"{API}/overview", headers=h(tokens["manager"])).json()
        assert ov["department"]["name"] == "Engineering"
        names = {m["name"] for m in ov["members"]}
        assert "Arjun Mehta" in names and "Oliver Grant" not in names
        depts = requests.get(f"{API}/org/departments", headers=h(tokens["manager"])).json()
        assert [d["name"] for d in depts] == ["Engineering"]

    def test_individual_lending(self, tokens):
        ov = requests.get(f"{API}/overview", headers=h(tokens["individual"])).json()
        assert "lending" in ov and ov["lending"]["lent_outstanding"] == 200 and ov["lending"]["borrowed_outstanding"] == 250

    def test_fresh_user_empty(self):
        r, _ = register()
        tok = r.json()["access_token"]
        us = requests.get(f"{API}/usage", headers=h(tok)).json()
        assert us["totals"]["credits"] == 0
        ov = requests.get(f"{API}/overview", headers=h(tok))
        assert ov.status_code == 200 and ov.json()["cycle"]["used"] == 0

    def test_fresh_org_admin_overview(self):
        r, _ = register(mode="organisation", org_name="TEST_Org2")
        tok = r.json()["access_token"]
        for p in ("overview", "usage", "org", "org/departments", "team/members"):
            assert requests.get(f"{API}/{p}", headers=h(tok)).status_code == 200, p

    def test_openapi(self):
        r = requests.get(f"{API}/openapi.json")
        assert r.status_code == 200 and "/api/demo/switch" in r.json()["paths"]
