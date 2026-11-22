"""Orqestra MVP: tasks, decomposition, dependencies, allocation recommendations, slot suggestions, privacy."""
import io
from datetime import datetime, timedelta, timezone
import httpx
from conftest import BASE, demo, new_user

ADMIN, MANAGER, EMPLOYEE, INDIVIDUAL = "admin", "manager", "employee", "individual"


def _goal_body(subtasks, title="Build the export API for invoices"):
    deadline = (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat()
    return {"title": title, "description": "Endpoint, tests and docs", "priority": "high", "deadline": deadline,
            "method": "rules", "subtasks": subtasks}


def _decompose(h, title="Build the export API for invoices", desc="Endpoint, tests and docs"):
    r = httpx.post(f"{BASE}/tasks/decompose", headers=h, json={"title": title, "description": desc, "priority": "high"})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- decomposition ----------

def test_decompose_rules_software_has_parallel_waves():
    d = _decompose(demo(MANAGER))
    assert d["method"] == "rules" and d["category"] == "software"
    subs = d["subtasks"]
    assert 4 <= len(subs) <= 12
    for s in subs:
        assert s["estimate_low"] <= s["estimate_high"] and s["provider_id"] and s["tool_reason"]
    # implement + tests both depend only on design -> same wave (parallel)
    assert subs[2]["depends_on"] == subs[3]["depends_on"] == [1]


def test_decompose_categories():
    h = demo(INDIVIDUAL)
    assert _decompose(h, "Research competitor pricing", "")["category"] == "research"
    assert _decompose(h, "Write a blog post about our launch", "")["category"] in ("content", "launch")
    assert _decompose(h, "Plan a team offsite", "")["category"] == "general"


def test_decompose_requires_title():
    r = httpx.post(f"{BASE}/tasks/decompose", headers=demo(EMPLOYEE), json={"title": "  "})
    assert r.status_code == 422


# ---------- goals, dependencies, waves ----------

def _create(h, subtasks=None, title="Build the export API for invoices"):
    subs = subtasks if subtasks is not None else [
        {**s, "basis": "rules"} for s in _decompose(h, title)["subtasks"]]
    r = httpx.post(f"{BASE}/tasks", headers=h, json=_goal_body(subs, title))
    assert r.status_code == 200, r.text
    return r.json()


def test_create_goal_computes_waves_and_blockers():
    g = _create(demo(MANAGER))
    subs = g["subtasks"]
    assert g["progress"]["total"] == len(subs) and g["waves"] >= 3
    assert subs[0]["wave"] == 0 and subs[1]["wave"] == 1 and subs[2]["wave"] == subs[3]["wave"] == 2
    assert subs[2]["blocked_by"] == [subs[1]["id"]]
    assert all(s["estimate"]["provenance"] for s in subs)


def test_cycle_is_rejected():
    h = demo(MANAGER)
    subs = [{"title": "A", "type": "code", "depends_on": [1], "estimate_low": 10, "estimate_high": 20},
            {"title": "B", "type": "code", "depends_on": [0], "estimate_low": 10, "estimate_high": 20}]
    r = httpx.post(f"{BASE}/tasks", headers=h, json=_goal_body(subs))
    assert r.status_code == 422 and "loop" in r.text


def test_bad_estimates_rejected():
    subs = [{"title": "A", "type": "code", "depends_on": [], "estimate_low": 50, "estimate_high": 10}]
    r = httpx.post(f"{BASE}/tasks", headers=demo(MANAGER), json=_goal_body(subs))
    assert r.status_code == 422


def test_cannot_start_blocked_subtask_then_can_after_dependency_done():
    h = demo(MANAGER)
    subs = [{"title": "Design", "type": "planning", "depends_on": [], "estimate_low": 10, "estimate_high": 20},
            {"title": "Build", "type": "code", "depends_on": [0], "estimate_low": 10, "estimate_high": 20}]
    g = _create(h, subs)
    a, b = g["subtasks"]
    r = httpx.patch(f"{BASE}/subtasks/{b['id']}", headers=h, json={"status": "in_progress"})
    assert r.status_code == 409 and "Waiting on" in r.text
    assert httpx.patch(f"{BASE}/subtasks/{a['id']}", headers=h, json={"status": "done", "output_summary": "Design agreed"}).status_code == 200
    r = httpx.patch(f"{BASE}/subtasks/{b['id']}", headers=h, json={"status": "in_progress"})
    assert r.status_code == 200


def test_goal_close_requires_all_done_and_builds_summary():
    h = demo(MANAGER)
    g = _create(h, [{"title": "Only step", "type": "writing", "depends_on": [], "estimate_low": 10, "estimate_high": 20}])
    assert httpx.patch(f"{BASE}/tasks/{g['id']}", headers=h, json={"status": "done"}).status_code == 409
    sid = g["subtasks"][0]["id"]
    httpx.patch(f"{BASE}/subtasks/{sid}", headers=h, json={"status": "done", "output_summary": "Wrote it"})
    r = httpx.patch(f"{BASE}/tasks/{g['id']}", headers=h, json={"status": "done"})
    assert r.status_code == 200 and r.json()["status"] == "done" and "Wrote it" in r.json()["summary"]


# ---------- assignment & resource allocation ----------

def test_candidates_ranked_with_reasons_and_assignment_notifies():
    h = demo(MANAGER)
    g = _create(h)
    sid = g["subtasks"][2]["id"]
    r = httpx.get(f"{BASE}/subtasks/{sid}/candidates", headers=h)
    assert r.status_code == 200, r.text
    c = r.json()
    assert 1 <= len(c["candidates"]) <= 3 and all(x["reason"] for x in c["candidates"])
    assert c["candidates"][0]["score"] >= c["candidates"][-1]["score"]
    assert c["capacity_options"] and all("Provider limits" in o["note"] or "own" in o["note"] or "budget" in o["note"].lower()
                                         for o in c["capacity_options"])
    r = httpx.patch(f"{BASE}/subtasks/{sid}", headers=h, json={"assignee_id": "usr_arjun_mehta"})
    assert r.status_code == 200
    notes = httpx.get(f"{BASE}/notifications", headers=demo(EMPLOYEE)).json()
    assert any(n["type"] == "task.assigned" for n in notes["items"])


def test_employee_sees_qualitative_capacity_for_colleagues():
    h = demo(EMPLOYEE)
    g = _create(h)
    c = httpx.get(f"{BASE}/subtasks/{g['subtasks'][0]['id']}/candidates", headers=h).json()
    others = [x for x in c["all"] if not x["is_you"]]
    assert others and all(x["headroom"] is None and "credits free" not in x["reason"] for x in others)
    me = [x for x in c["all"] if x["is_you"]][0]
    assert me["headroom"] is not None


def test_cannot_assign_outside_workspace():
    g = _create(demo(INDIVIDUAL), title="Research onboarding flows")
    r = httpx.patch(f"{BASE}/subtasks/{g['subtasks'][0]['id']}", headers=demo(INDIVIDUAL), json={"assignee_id": "usr_arjun_mehta"})
    assert r.status_code == 400


def test_other_users_cannot_see_goal():
    g = _create(demo(INDIVIDUAL), title="Research onboarding flows")
    assert httpx.get(f"{BASE}/tasks/{g['id']}", headers=demo(EMPLOYEE)).status_code == 403
    _, stranger = new_user()
    assert httpx.get(f"{BASE}/tasks/{g['id']}", headers=stranger).status_code == 403


def test_assignee_can_update_status_but_not_reassign():
    h = demo(MANAGER)
    g = _create(h, [{"title": "Solo", "type": "code", "depends_on": [], "estimate_low": 10, "estimate_high": 20}])
    sid = g["subtasks"][0]["id"]
    httpx.patch(f"{BASE}/subtasks/{sid}", headers=h, json={"assignee_id": "usr_arjun_mehta"})
    e = demo(EMPLOYEE)
    assert httpx.patch(f"{BASE}/subtasks/{sid}", headers=e, json={"status": "in_progress"}).status_code == 200
    assert httpx.patch(f"{BASE}/subtasks/{sid}", headers=e, json={"assignee_id": "usr_noah_kim"}).status_code == 403
    assert any(x["id"] == g["id"] for x in httpx.get(f"{BASE}/tasks", headers=e).json()["goals"])


# ---------- planner slot suggestions ----------

def test_slot_requires_assignee_then_suggests_free_working_hours_slot():
    h = demo(EMPLOYEE)
    g = _create(h, [{"title": "Write tests", "type": "code", "depends_on": [], "estimate_low": 100, "estimate_high": 300}])
    sid = g["subtasks"][0]["id"]
    assert httpx.post(f"{BASE}/subtasks/{sid}/slot", headers=h, json={"tz_offset": -330}).status_code == 409
    httpx.patch(f"{BASE}/subtasks/{sid}", headers=h, json={"assignee_id": "usr_arjun_mehta"})
    r = httpx.post(f"{BASE}/subtasks/{sid}/slot", headers=h, json={"tz_offset": -330})
    assert r.status_code == 200, r.text
    s = r.json()
    start = datetime.fromisoformat(s["start_at"]).astimezone(timezone(timedelta(minutes=330)))
    end = datetime.fromisoformat(s["end_at"]).astimezone(timezone(timedelta(minutes=330)))
    assert 9 <= start.hour and (end.hour < 18 or (end.hour == 18 and end.minute == 0)) and start.weekday() < 5
    assert (end - start) == timedelta(minutes=90) and s["reasons"] and s["provenance"]["estimate"]
    # scheduling as the assignee creates a linked planner session with no overlap
    r = httpx.post(f"{BASE}/subtasks/{sid}/schedule", headers=h, json={"start_at": s["start_at"], "end_at": s["end_at"]})
    assert r.status_code == 200 and r.json()["scheduled"] and r.json()["warning"] is None
    sub = [x for x in r.json()["goal"]["subtasks"] if x["id"] == sid][0]
    assert sub["session_id"]
    # a second suggestion for a new task avoids the slot just booked
    g2 = _create(h, [{"title": "More tests", "type": "code", "depends_on": [], "estimate_low": 100, "estimate_high": 300}])
    sid2 = g2["subtasks"][0]["id"]
    httpx.patch(f"{BASE}/subtasks/{sid2}", headers=h, json={"assignee_id": "usr_arjun_mehta"})
    s2 = httpx.post(f"{BASE}/subtasks/{sid2}/slot", headers=h, json={"tz_offset": -330}).json()
    assert s2["start_at"] >= s["end_at"] or s2["end_at"] <= s["start_at"]


def test_owner_schedule_for_someone_else_becomes_suggestion():
    h = demo(MANAGER)
    g = _create(h, [{"title": "Docs", "type": "writing", "depends_on": [], "estimate_low": 50, "estimate_high": 100}])
    sid = g["subtasks"][0]["id"]
    httpx.patch(f"{BASE}/subtasks/{sid}", headers=h, json={"assignee_id": "usr_arjun_mehta"})
    s = httpx.post(f"{BASE}/subtasks/{sid}/slot", headers=h, json={"tz_offset": 0}).json()
    r = httpx.post(f"{BASE}/subtasks/{sid}/schedule", headers=h, json={"start_at": s["start_at"], "end_at": s["end_at"]})
    assert r.status_code == 200 and r.json()["suggested"] and not r.json()["scheduled"]


# ---------- privacy: handover content restricted to sender and recipient ----------

def _seeded_handover(h):
    items = httpx.get(f"{BASE}/handovers", headers=h, params={"box": "all"}).json()["tasks"]
    return [t for t in items if t["creator_id"] != "usr_daniel_okafor" and t["assignee_id"] != "usr_daniel_okafor"][0]


def test_admin_sees_handover_metadata_only():
    admin = demo(ADMIN)
    t = _seeded_handover(admin)
    assert t["content_restricted"] is True
    d = httpx.get(f"{BASE}/handovers/{t['id']}", headers=admin).json()
    for field in ("objective", "context_notes", "pending_work", "completed_work", "description"):
        assert field not in d
    assert d["attachments"] == [] and d["title"] and d["status"]


def test_parties_still_see_full_content_and_attachments_roundtrip():
    sofia = demo(MANAGER)
    body = {"title": "Privacy check handover", "objective": "Secret objective", "pending_work": "Pending bits",
            "context_notes": "Private notes", "assignee_id": "usr_arjun_mehta", "priority": "medium"}
    r = httpx.post(f"{BASE}/handovers", headers=sofia, json=body)
    assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]
    data = b"hello orqestra"
    up = httpx.post(f"{BASE}/handovers/{tid}/attachments", headers=sofia, files={"file": ("notes.txt", io.BytesIO(data), "text/plain")})
    assert up.status_code in (200, 201), up.text
    arjun = demo(EMPLOYEE)
    d = httpx.get(f"{BASE}/handovers/{tid}", headers=arjun).json()
    assert d["objective"] == "Secret objective" and d["content_restricted"] is False and len(d["attachments"]) == 1
    dl = httpx.get(f"{BASE}/handovers/{tid}/attachments/{d['attachments'][0]['id']}", headers=arjun)
    assert dl.status_code == 200 and dl.content == data
    admin = demo(ADMIN)
    assert "objective" not in httpx.get(f"{BASE}/handovers/{tid}", headers=admin).json()
    assert httpx.get(f"{BASE}/handovers/{tid}/attachments/{d['attachments'][0]['id']}", headers=admin).status_code == 403
    # duplicate submission within 2 minutes is refused
    assert httpx.post(f"{BASE}/handovers", headers=sofia, json=body).status_code == 409
    httpx.post(f"{BASE}/handovers/{tid}/cancel", headers=sofia, json={"note": ""})


# ---------- allocation suggestions & independence ----------

def test_admin_gets_cross_department_suggestions():
    s = httpx.get(f"{BASE}/allocation", headers=demo(ADMIN), params={"days": 30}).json()["suggestions"]
    assert s, "expected at least one suggestion for the seeded data"
    assert any(x["cross_department"] for x in s)


def test_public_config_and_google_disabled():
    assert httpx.get(f"{BASE}/config").json()["google_auth"] is False
    r = httpx.post(f"{BASE}/auth/google/session", json={"session_id": "x"})
    assert r.status_code == 503


def test_tasks_module_visible_to_all_roles():
    for key in (ADMIN, MANAGER, EMPLOYEE, INDIVIDUAL):
        me = httpx.get(f"{BASE}/auth/me", headers=demo(key)).json()
        assert "tasks" in me["allowed_modules"]
