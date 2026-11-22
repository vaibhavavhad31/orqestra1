import httpx
from conftest import BASE, demo, new_user
def test_demo_switch_ok():
    r = httpx.post(f"{BASE}/demo/switch", json={"target_user_id":"usr_sofia_marchetti"}, headers=demo("admin"))
    assert r.status_code==200, r.text
def test_real_user_forbidden():
    _, h = new_user()
    assert httpx.post(f"{BASE}/demo/switch", json={"target_user_id":"usr_sofia_marchetti"}, headers=h).status_code==403
def test_switch_to_non_demo_forbidden():
    r = httpx.post(f"{BASE}/demo/switch", json={"target_user_id":"usr_lena_fischer"}, headers=demo("admin"))
    assert r.status_code in (403,404)
