import time, httpx
from p3_helpers import BASE, DB, login, session, ses_of, iso, tag, datetime, timedelta, timezone, ARJUN, MAYA, SOFIA, DANIEL

def test_session_validation_overlap_edit_cancel_complete():
    a = login(ARJUN)
    r = session(a); assert r.status_code in (200, 201), r.text; s = ses_of(r)
    assert DB.audit_log.find_one({"action": "session.created", "meta.session_id": s["id"]})
    assert session(a, start_offset=-timedelta(hours=2)).status_code == 422
    assert session(a, dur=-30).status_code == 422
    assert session(a, credits=0).status_code == 422
    st = datetime.fromisoformat(s["start_at"])
    ov = httpx.post(f"{BASE}/planner/sessions", headers=a, json={"provider_id": "claude", "start_at": iso(st + timedelta(minutes=10)),
         "end_at": iso(st + timedelta(minutes=40)), "estimated_credits": 50, "purpose": tag("ov")})
    assert ov.status_code in (200, 201) and ov.json().get("warning") == "Overlaps another session"
    e = httpx.patch(f"{BASE}/planner/sessions/{s['id']}", headers=a, json={"estimated_credits": 222})
    assert e.status_code == 200, e.text
    got = [x for x in httpx.get(f"{BASE}/planner/sessions", headers=a).json()["sessions"] if x["id"] == s["id"]][0]
    assert got["estimated_credits"] == 222
    assert httpx.post(f"{BASE}/planner/sessions/{ses_of(ov)['id']}/cancel", headers=a).status_code == 200
    assert httpx.post(f"{BASE}/planner/sessions/{s['id']}/complete", headers=a).status_code == 200

def test_reminder_exactly_once():
    a = login(ARJUN)
    s = ses_of(session(a, start_offset=timedelta(minutes=20), reminder=30))
    deadline = time.time() + 130
    while time.time() < deadline:
        n = DB.notifications.count_documents({"type": "session.reminder", "meta.session_id": s["id"]})
        if n: break
        time.sleep(5)
    time.sleep(65)
    assert DB.notifications.count_documents({"type": "session.reminder", "meta.session_id": s["id"]}) == 1
    httpx.post(f"{BASE}/planner/sessions/{s['id']}/cancel", headers=a)

def test_resets_and_disclaimer():
    a = login(ARJUN)
    r = httpx.post(f"{BASE}/planner/resets", headers=a, json={"provider_id": "claude", "reset_type": "rolling", "rolling_hours": 5, "next_reset_at": iso(datetime.now(timezone.utc) + timedelta(hours=5))})
    assert r.status_code in (200, 201), r.text
    g = httpx.get(f"{BASE}/planner/resets", headers=a).text; assert "claude" in g
    assert "Entered by you" in g or "self" in g.lower() or "user" in g.lower()
    assert "does not create extra provider capacity" in httpx.get(f"{BASE}/planner/sessions", headers=a).text
    j = r.json(); j = j if isinstance(j, dict) else {"resets": j}; rid = (j.get("reset") or {}).get("id") or next((x["id"] for x in j.get("resets", []) if x.get("provider_id") == "claude"), None)
    if rid: httpx.delete(f"{BASE}/planner/resets/{rid}", headers=a)

def test_team_planner_suggest_access():
    a, sf, d = login(ARJUN), login(SOFIA), login(DANIEL)
    s = ses_of(session(a, start_offset=timedelta(days=2)))
    t = httpx.get(f"{BASE}/planner/team", headers=sf); assert t.status_code == 200
    assert any(x["id"] == s["id"] for x in t.json()["sessions"])
    assert all(x.get("department_id") in (None, "dep_engineering") for x in t.json()["sessions"])
    f = httpx.get(f"{BASE}/planner/team?member_id=usr_arjun_mehta", headers=sf).json()["sessions"]
    assert f and all(x["user_id"] == "usr_arjun_mehta" for x in f)
    dd = httpx.get(f"{BASE}/planner/team", headers=d).json()["sessions"]
    assert len({x.get("department_id") for x in dd}) >= 1 and len(dd) >= len(t.json()["sessions"])
    ns = datetime.fromisoformat(s["start_at"]) + timedelta(hours=3)
    sg = httpx.post(f"{BASE}/planner/team/sessions/{s['id']}/suggest", headers=sf, json={"start_at": iso(ns), "end_at": iso(ns + timedelta(hours=1)), "note": "tscheck"})
    assert sg.status_code == 200, sg.text
    assert DB.notifications.find_one({"type": "session.suggestion", "user_id": "usr_arjun_mehta", "meta.session_id": s["id"]})
    ac = httpx.post(f"{BASE}/planner/sessions/{s['id']}/suggestion/accept", headers=a); assert ac.status_code == 200
    got = [x for x in httpx.get(f"{BASE}/planner/sessions", headers=a).json()["sessions"] if x["id"] == s["id"]][0]
    assert datetime.fromisoformat(got["start_at"]) == ns
    assert httpx.get(f"{BASE}/planner/team", headers=a).status_code == 403
    assert httpx.get(f"{BASE}/planner/team", headers=login(MAYA)).status_code == 403
    httpx.post(f"{BASE}/planner/sessions/{s['id']}/cancel", headers=a)
