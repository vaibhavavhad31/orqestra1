import httpx, uuid
from conftest import BASE, new_user
def test_login_ok_and_bad():
    r = httpx.post(f"{BASE}/auth/login", json={"email":"arjun.mehta@nexora.io","password":"Demo@12345"}); assert r.status_code==200
    r = httpx.post(f"{BASE}/auth/login", json={"email":f"tscheck-nouser-{uuid.uuid4().hex[:6]}@x.com","password":"wrongpass1"}); assert r.status_code in (400,401)
def test_register_validation_and_me():
    email, h = new_user()
    me = httpx.get(f"{BASE}/auth/me", headers=h); assert me.status_code==200 and me.json().get("email", me.text)
    dup = httpx.post(f"{BASE}/auth/register", json={"name":"x","email":email,"password":"Tscheck@123","mode":"individual"}); assert dup.status_code in (400,409,422)
    short = httpx.post(f"{BASE}/auth/register", json={"name":"x","email":f"tscheck-{uuid.uuid4().hex[:6]}@x.com","password":"short","mode":"individual"}); assert short.status_code in (400,422)
def test_me_unauth():
    assert httpx.get(f"{BASE}/auth/me").status_code==401
