import uuid, httpx, pytest
BASE = "http://localhost:8001/api"
def demo(key):
    r = httpx.post(f"{BASE}/demo/login", json={"key": key}); assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
def new_user(mode="individual"):
    email = f"tscheck-{uuid.uuid4().hex[:8]}@example.com"
    body = {"name": "tscheck user", "email": email, "password": "Tscheck@123", "mode": mode}
    if mode == "organisation": body["org_name"] = f"tscheck-org-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/auth/register", json=body); assert r.status_code in (200, 201), r.text
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}
@pytest.fixture
def base(): return BASE
