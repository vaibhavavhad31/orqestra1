import httpx
from conftest import BASE, demo
def g(h, **p): return httpx.get(f"{BASE}/usage", headers=h, params=p)
def test_admin_filters():
    h = demo("admin")
    for d in (7, 30, 90):
        r = g(h, days=d).json(); assert r["days"] == d
        assert sum(p["credits"] for p in r["providers"]) == r["totals"]["credits"]
    r = g(h, days=30, provider="claude").json(); assert all(p["id"] == "claude" for p in r["providers"] if p["credits"])
    r = g(h, days=30, department_id="dep_marketing").json(); assert r["totals"]["credits"] > 0
    r = g(h, days=30, member_id="usr_arjun_mehta").json(); assert r["totals"]["credits"] > 0
def test_scope_403():
    m = demo("manager")
    assert g(m, member_id="usr_arjun_mehta").status_code == 200
    assert g(m, member_id="usr_aisha_bello").status_code == 403
    assert g(m, department_id="dep_marketing").status_code == 403
    e = demo("employee")
    assert g(e, member_id="usr_noah_kim").status_code == 403
    assert g(demo("individual"), department_id="dep_engineering").status_code == 403
