import hashlib, httpx, os
from p3_helpers import BASE, DB, login, handover, task_of, ARJUN, SOFIA, DANIEL, MAYA, TOMAS, HANA

def eng_colleague(h):
    a = httpx.get(f"{BASE}/handovers/assignees", headers=h).json()
    return next(x["id"] for x in a if x["department_id"] == "dep_engineering")

def test_create_attach_download_hash():
    a = login(ARJUN); r = handover(a, eng_colleague(a)); assert r.status_code in (200, 201), r.text
    t = task_of(r); assert t["status"] == "pending"
    pdf = b"%PDF-1.4\n" + os.urandom(2048) + b"\n%%EOF"
    up = httpx.post(f"{BASE}/handovers/{t['id']}/attachments", headers=a, files={"file": ("tscheck.pdf", pdf, "application/pdf")})
    assert up.status_code == 200, up.text
    j = up.json(); aid = j.get("id") or j.get("attachment", {}).get("id") or j.get("attachment_id")
    assert aid, j
    dl = httpx.get(f"{BASE}/handovers/{t['id']}/attachments/{aid}", headers=a); assert dl.status_code == 200
    assert hashlib.sha256(dl.content).hexdigest() == hashlib.sha256(pdf).hexdigest()
    sent = httpx.get(f"{BASE}/handovers?box=sent", headers=a).json()["tasks"]; assert any(x["id"] == t["id"] for x in sent)
    httpx.get(f"{BASE}/handovers?box=received", headers=login(SOFIA if False else ARJUN)).json()
    # bad files
    exe = httpx.post(f"{BASE}/handovers/{t['id']}/attachments", headers=a, files={"file": ("x.exe", b"MZ" * 10, "application/octet-stream")})
    assert exe.status_code >= 400 and "Unsupported file or file too large (max 10 MB)" in exe.text
    big = httpx.post(f"{BASE}/handovers/{t['id']}/attachments", headers=a, files={"file": ("b.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024 + 10), "application/pdf")})
    assert big.status_code >= 400 and "max 10 MB" in big.text
    # non-party cannot see task or attachment
    mk = login(MAYA)
    assert httpx.get(f"{BASE}/handovers/{t['id']}", headers=mk).status_code in (403, 404)
    assert httpx.get(f"{BASE}/handovers/{t['id']}/attachments/{aid}", headers=mk).status_code in (403, 404)
    # records
    assert DB.audit_log.find_one({"action": "handover.created", "meta.task_id": t["id"]})
    assert DB.notifications.find_one({"type": "handover.received", "meta.task_id": t["id"]})

def test_validation():
    a = login(ARJUN); r = handover(a, eng_colleague(a), pending_work=""); assert r.status_code == 422 and "pending_work" in r.text
    r = httpx.post(f"{BASE}/handovers", headers=a, json={"title": "", "pending_work": "x", "assignee_id": eng_colleague(a)})
    assert r.status_code == 422 and "title" in r.text

def test_assignee_rules_and_flow():
    m, tm = login(MAYA), login(TOMAS)
    tid_tomas = "usr_tomas_reyes"
    assert handover(m, "usr_arjun_mehta").status_code in (400, 403, 422)
    bad = handover(m, "usr_arjun_mehta"); assert "You can't hand over to this user" in bad.text
    t = task_of(handover(m, tid_tomas))
    assert httpx.post(f"{BASE}/handovers/{t['id']}/complete", headers=tm).status_code == 409
    assert httpx.get(f"{BASE}/handovers/{t['id']}", headers=login(HANA)).status_code == 403
    assert httpx.post(f"{BASE}/handovers/{t['id']}/accept", headers=tm).status_code == 200
    c = httpx.post(f"{BASE}/handovers/{t['id']}/complete", headers=tm); assert c.status_code == 200
    d = httpx.get(f"{BASE}/handovers/{t['id']}", headers=m).json(); d = d.get("task", d)
    acts = [h["action"] for h in d["history"]]; assert "accepted" in str(acts) and "completed" in str(acts)
    assert all(h.get("actor_id") and h.get("at") for h in d["history"])
    # reject
    t2 = task_of(handover(m, tid_tomas))
    assert httpx.post(f"{BASE}/handovers/{t2['id']}/reject", headers=tm, json={"note": "tscheck-reason"}).status_code == 200
    assert "tscheck-reason" in httpx.get(f"{BASE}/handovers/{t2['id']}", headers=m).text
    t3 = task_of(handover(m, tid_tomas))
    cc = httpx.post(f"{BASE}/handovers/{t3['id']}/cancel", headers=m); assert cc.status_code == 200 and "cancel" in cc.text

def test_visibility_all_scopes():
    s = httpx.get(f"{BASE}/handovers?box=all", headers=login(SOFIA)); assert s.status_code == 200
    j = s.json(); assert "chat history" in j.get("privacy_note", "").lower()
    ids = {x["creator_id"] for x in j["tasks"]} | {x["assignee_id"] for x in j["tasks"]}
    users = {u["id"]: u.get("department_id") for u in DB.users.find({"id": {"$in": list(ids)}}, {"id": 1, "department_id": 1})}
    for x in j["tasks"]:
        assert "dep_engineering" in (users.get(x["creator_id"]), users.get(x["assignee_id"])), x["id"]
    assert not any("chat" in k for x in j["tasks"] for k in x)
    d = httpx.get(f"{BASE}/handovers?box=all", headers=login(DANIEL)); assert d.status_code == 200
    assert len(d.json()["tasks"]) >= len(j["tasks"])
    assert httpx.get(f"{BASE}/handovers?box=all", headers=login(ARJUN)).status_code in (200, 403)
