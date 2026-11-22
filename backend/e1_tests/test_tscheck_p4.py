import uuid, httpx
from conftest import BASE, demo, new_user

def G(h, p): return httpx.get(BASE + p, headers=h, timeout=30)
def P(h, p, j=None): return httpx.post(BASE + p, headers=h, json=j or {}, timeout=30)
def PA(h, p, j): return httpx.patch(BASE + p, headers=h, json=j, timeout=30)
def PUT(h, p, j): return httpx.put(BASE + p, headers=h, json=j, timeout=30)
def login(email, pw): return httpx.post(BASE + "/auth/login", json={"email": email, "password": pw}, timeout=30)
def tok(r): return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_notifications():
    e, s, a = demo("employee"), demo("manager"), demo("admin")
    before = G(s, "/notifications/unread-count").json()["unread"]
    rq = P(e, "/allocation/requests", {"amount": 5, "reason": "tscheck-p4-notif", "urgency": "low"}).json()
    try:
        assert G(s, "/notifications/unread-count").json()["unread"] == before + 1
        items = G(s, "/notifications").json()["items"]
        n = items[0]; assert n["link"] and not n["read"]
        assert P(a, f"/notifications/{n['id']}/read").status_code in (403, 404)
        assert G(a, f"/notifications/{n['id']}").status_code in (403, 404)
        assert P(s, f"/notifications/{n['id']}/read").status_code == 200
        assert G(s, "/notifications/unread-count").json()["unread"] == before
        assert G(s, "/notifications/pending").json()["total"] >= 1
    finally:
        P(e, f"/allocation/requests/{rq['id']}/cancel")
    _, h = new_user()
    assert P(h, "/notifications/read-all").status_code == 200
    assert G(h, "/notifications/unread-count").json()["unread"] == 0

def test_reports():
    a, s, e, m = demo("admin"), demo("manager"), demo("employee"), demo("individual")
    for d in (7, 30, 90):
        r = G(a, f"/reports/usage?days={d}").json(); u = G(a, f"/usage?days={d}").json()
        assert r["label"] == "Simulated data" and r["totals"]["credits"] == u["totals"]["credits"]
        assert G(a, f"/reports/allocation?days={d}").status_code == 200
    csv = G(a, "/reports/usage/csv?days=30"); assert csv.status_code == 200
    assert "Simulated data" in csv.text and "Provider,Credits" in csv.text
    assert str(G(a, "/reports/usage?days=30").json()["totals"]["credits"]) in csv.text
    sr = G(s, "/reports/usage?days=30").json(); assert "Engineering" in str(sr["scope"])
    mr = G(m, "/reports/usage?days=30").json(); assert "Nexora" not in str(mr)
    lr = G(m, "/reports/lending?days=30"); assert lr.status_code == 200 and lr.json()["summary"] and "Nexora" not in lr.text
    assert G(e, "/reports/usage?days=30").status_code == 403
    assert G(e, "/reports/usage/csv?days=30").status_code == 403

def test_team_management():
    a, s, e, m = demo("admin"), demo("manager"), demo("employee"), demo("individual")
    _, oh = new_user("organisation")  # own org: members/departments cannot be deleted
    dep = G(oh, "/org/departments").json()[0]["id"] if G(oh, "/org/departments").json() else P(oh, "/org/departments", {"name": "tscheck-d"}).json()["id"]
    email = f"tscheck-p4-{uuid.uuid4().hex[:6]}@example.com"
    r = P(oh, "/team/members", {"name": "tscheck p4", "email": email, "role": "employee", "department_id": dep, "title": "t"})
    assert r.status_code in (200, 201), r.text
    body = r.json(); temp = body.get("temp_password") or body.get("temporary_password")
    mid = (body.get("member") or body)["id"]; assert temp, body
    assert P(oh, "/team/members", {"name": "dup", "email": email, "role": "employee", "department_id": dep}).status_code in (400, 409, 422)
    assert login(email, temp).status_code == 200
    assert PA(oh, f"/team/members/{mid}", {"role": "manager"}).status_code == 200
    assert login(email, temp).json()["user"]["role"] == "manager"
    assert P(oh, f"/team/members/{mid}/deactivate").status_code == 200
    r = login(email, temp); assert r.status_code in (401, 403) and "deactivated" in r.text
    assert P(a, "/team/members/usr_daniel_okafor/deactivate").status_code in (400, 403)
    assert P(a, "/team/members/usr_arjun_mehta/deactivate").status_code in (400, 403)
    assert any(x["email"] == email for x in G(oh, "/team/members?q=tscheck-p4").json()["members"])
    dn = f"tscheck-dept-{uuid.uuid4().hex[:4]}"
    d = P(oh, "/org/departments", {"name": dn}); assert d.status_code in (200, 201), d.text
    did = d.json()["id"]
    assert PA(oh, f"/org/departments/{did}", {"name": dn + "-r"}).status_code == 200
    assert G(s, "/team/members").status_code == 200
    assert P(s, "/team/members", {"name": "x", "email": "tscheck-x@example.com", "role": "employee"}).status_code == 403
    assert P(s, "/org/departments", {"name": "tscheck-x"}).status_code == 403
    for h in (e, m): assert G(h, "/team/members").status_code == 403

def test_integrations():
    for k in ("admin", "individual"):
        h = demo(k); j = G(h, "/integrations").json()
        assert len(j["providers"]) == 5 and j["note"] == "No real provider data is retrieved."
        pid = j["providers"][0]["id"]; orig = j["providers"][0]["simulated_connection"]
        try:
            assert PUT(h, f"/integrations/{pid}", {"enabled": True}).status_code == 200
            p = [x for x in G(h, "/integrations").json()["providers"] if x["id"] == pid][0]
            assert p["status"] == "Simulated connection active"
        finally:
            PUT(h, f"/integrations/{pid}", {"enabled": orig})
    for k in ("manager", "employee"):
        assert G(demo(k), "/integrations").status_code == 403

def test_settings():
    email, h = new_user()
    assert PA(h, "/settings/profile", {"name": "tscheck renamed", "title": "QA"}).status_code == 200
    assert G(h, "/settings").json()["profile"]["name"] == "tscheck renamed"
    r = P(h, "/settings/password", {"current_password": "wrong", "new_password": "Tscheck@456", "confirm_password": "Tscheck@456"})
    assert r.status_code in (400, 401, 403, 422)
    assert P(h, "/settings/password", {"current_password": "Tscheck@123", "new_password": "Tscheck@456", "confirm_password": "Tscheck@456"}).status_code == 200
    assert login(email, "Tscheck@456").status_code == 200
    r = P(demo("employee"), "/settings/password", {"current_password": "Demo@12345", "new_password": "X@1234567", "confirm_password": "X@1234567"})
    assert r.status_code in (400, 403) and "disabled for demo accounts" in r.text
    # org rename on a tscheck org
    _, oh = new_user("organisation")
    assert PA(oh, "/org", {"name": "tscheck-renamed-org"}).status_code == 200
    assert G(oh, "/org").json()["name"] == "tscheck-renamed-org"
    assert PA(demo("manager"), "/org", {"name": "tscheck-bad"}).status_code == 403
    assert G(demo("admin"), "/org").json()["name"] == "Nexora Technologies"
