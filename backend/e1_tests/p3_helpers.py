import uuid, httpx
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
BASE = "http://localhost:8001/api"
DB = MongoClient("mongodb://localhost:27017").test_database  # read-only use

def login(email):
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": "Demo@12345"}); assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

ARJUN, SOFIA, DANIEL = "arjun.mehta@nexora.io", "sofia.marchetti@nexora.io", "daniel.okafor@nexora.io"
MAYA, TOMAS, HANA = "maya.ellison@indie.dev", "tomas.reyes@indie.dev", "hana.sato@indie.dev"

def tag(s): return f"tscheck-{s}-{uuid.uuid4().hex[:6]}"

def handover(h, assignee, title=None, **kw):
    body = {"title": title or tag("hnd"), "objective": "obj", "priority": "medium", "completed_work": "done",
            "pending_work": "todo", "context_notes": "ctx", "assignee_id": assignee} | kw
    return httpx.post(f"{BASE}/handovers", json=body, headers=h)

def iso(dt): return dt.astimezone(timezone.utc).isoformat()

def session(h, start_offset=timedelta(days=1), dur=60, credits=100, reminder=None, purpose=None):
    s = datetime.now(timezone.utc) + start_offset
    body = {"provider_id": "claude", "start_at": iso(s), "end_at": iso(s + timedelta(minutes=dur)),
            "estimated_credits": credits, "purpose": purpose or tag("ses"), "reminder_min": reminder}
    return httpx.post(f"{BASE}/planner/sessions", json=body, headers=h)

def task_of(r):
    j = r.json(); return j.get("task", j)
def ses_of(r):
    j = r.json(); return j.get("session", j)
