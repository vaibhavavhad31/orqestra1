import logging
import random
from datetime import datetime, timedelta, timezone
from pymongo import UpdateOne
from core.config import DEMO_PASSWORD
from core.db import db, now_iso, now_utc, today_utc
from core.security import hash_password

log = logging.getLogger("seed")
ORG_ID = "org_nexora"
ORG_BUDGET = 50000
USAGE_DAYS = 90

PROVIDERS = [
    {"id": "chatgpt", "name": "ChatGPT", "vendor": "OpenAI", "color": "#10A37F", "credits_per_request": 2.0},
    {"id": "claude", "name": "Claude", "vendor": "Anthropic", "color": "#D97706", "credits_per_request": 2.5},
    {"id": "gemini", "name": "Gemini", "vendor": "Google", "color": "#2563EB", "credits_per_request": 1.8},
    {"id": "copilot", "name": "Copilot", "vendor": "GitHub / Microsoft", "color": "#6366F1", "credits_per_request": 1.2},
    {"id": "perplexity", "name": "Perplexity", "vendor": "Perplexity AI", "color": "#DB2777", "credits_per_request": 1.5},
]

DEPARTMENTS = [
    ("dep_engineering", "Engineering", 20000, "usr_sofia_marchetti"),
    ("dep_product", "Product", 11000, "usr_elena_petrova"),
    ("dep_marketing", "Marketing", 9000, "usr_aisha_bello"),
    ("dep_operations", "Operations", 6000, "usr_lena_fischer"),
]

ENG = {"copilot": 5, "claude": 4, "chatgpt": 2, "gemini": 1}
PROD = {"claude": 4, "chatgpt": 3, "gemini": 2, "perplexity": 1}
MKT = {"chatgpt": 5, "perplexity": 3, "gemini": 2, "claude": 1}
OPS = {"chatgpt": 4, "gemini": 3, "perplexity": 2, "claude": 1}

# id, name, email, title, role, dept, monthly allocation, target utilisation, provider weights, demo key
ORG_USERS = [
    ("usr_daniel_okafor", "Daniel Okafor", "daniel.okafor@nexora.io", "Chief Operating Officer", "admin", "dep_operations", 2000, 0.42, OPS, "admin"),
    ("usr_lena_fischer", "Lena Fischer", "lena.fischer@nexora.io", "Operations Manager", "manager", "dep_operations", 2000, 0.30, OPS, None),
    ("usr_marcus_bell", "Marcus Bell", "marcus.bell@nexora.io", "Finance & Ops Analyst", "employee", "dep_operations", 1500, 0.74, OPS, None),
    ("usr_sofia_marchetti", "Sofia Marchetti", "sofia.marchetti@nexora.io", "Head of Engineering", "manager", "dep_engineering", 3000, 0.55, ENG, "manager"),
    ("usr_arjun_mehta", "Arjun Mehta", "arjun.mehta@nexora.io", "Senior Backend Engineer", "employee", "dep_engineering", 5000, 0.90, ENG, "employee"),
    ("usr_chloe_martin", "Chloe Martin", "chloe.martin@nexora.io", "Frontend Engineer", "employee", "dep_engineering", 3500, 0.33, ENG, None),
    ("usr_ravi_iyer", "Ravi Iyer", "ravi.iyer@nexora.io", "Machine Learning Engineer", "employee", "dep_engineering", 5000, 0.93, ENG, None),
    ("usr_noah_kim", "Noah Kim", "noah.kim@nexora.io", "DevOps Engineer", "employee", "dep_engineering", 2500, 0.62, ENG, None),
    ("usr_elena_petrova", "Elena Petrova", "elena.petrova@nexora.io", "Head of Product", "manager", "dep_product", 4000, 0.70, PROD, None),
    ("usr_james_whitaker", "James Whitaker", "james.whitaker@nexora.io", "Senior Product Designer", "employee", "dep_product", 4500, 0.27, PROD, None),
    ("usr_aisha_bello", "Aisha Bello", "aisha.bello@nexora.io", "Marketing Lead", "manager", "dep_marketing", 3500, 0.96, MKT, None),
    ("usr_oliver_grant", "Oliver Grant", "oliver.grant@nexora.io", "Content Strategist", "employee", "dep_marketing", 4500, 0.98, MKT, None),
]

PERSONAL = {"chatgpt": 4, "claude": 3, "gemini": 2, "perplexity": 2, "copilot": 1}
INDIVIDUALS = [
    ("usr_maya_ellison", "Maya Ellison", "maya.ellison@indie.dev", "Independent UX Researcher", 2000, 0.68, PERSONAL, "individual"),
    ("usr_tomas_reyes", "Tomás Reyes", "tomas.reyes@indie.dev", "Freelance Developer", 1500, 0.86, ENG, "tomas"),
    ("usr_hana_sato", "Hana Sato", "hana.sato@indie.dev", "Graduate Researcher", 2500, 0.40, PROD, "hana"),
    ("usr_kwame_boateng", "Kwame Boateng", "kwame.boateng@indie.dev", "Content Creator", 1000, 0.92, MKT, "kwame"),
]

MAYA, TOMAS, HANA, KWAME = "usr_maya_ellison", "usr_tomas_reyes", "usr_hana_sato", "usr_kwame_boateng"
FRIENDSHIPS = [(MAYA, TOMAS, 60), (MAYA, HANA, 45), (KWAME, MAYA, 50), (TOMAS, HANA, 30)]

# id, initiator, lender, borrower, credits, repaid, status, note, created days ago, due in days (None = no due date)
LEDGER_V2 = [
    ("lnd_001", TOMAS, MAYA, TOMAS, 300, 100, "active", "Client sprint crunch", 21, -5),
    ("lnd_002", MAYA, HANA, MAYA, 250, 0, "active", "Research synthesis week", 9, 21),
    ("lnd_003", KWAME, MAYA, KWAME, 150, 150, "repaid", "Video script batch", 40, None),
    ("lnd_004", KWAME, MAYA, KWAME, 200, 0, "pending", "Launch week top-up", 2, 14),
    ("lnd_005", HANA, TOMAS, HANA, 120, 0, "declined", "Thesis deadline", 15, None),
]
# id, loan, amount, status, days ago
REPAYMENTS = [
    ("rep_001", "lnd_001", 100, "confirmed", 10),
    ("rep_002", "lnd_003", 150, "confirmed", 25),
    ("rep_003", "lnd_002", 50, "awaiting_confirmation", 1),
]



async def _upsert(collection: str, docs: list[dict]) -> None:
    if docs:
        await db[collection].bulk_write([UpdateOne({"id": d["id"]}, {"$setOnInsert": d}, upsert=True) for d in docs], ordered=False)


def _ago(days: int) -> str:
    return (today_utc() - timedelta(days=days)).isoformat()


async def _seed_core() -> None:
    now = now_iso()
    await _upsert("providers", [{**p, "sort_order": i, "simulated": True, "active": True, "status": "simulated",
                                 "connector": None, "created_at": now} for i, p in enumerate(PROVIDERS)])
    await _upsert("organizations", [{"id": ORG_ID, "name": "Nexora Technologies", "industry": "B2B software",
                                     "is_demo": True, "owner_id": "usr_daniel_okafor", "created_at": now}])
    await _upsert("departments", [{"id": d, "org_id": ORG_ID, "name": n, "manager_id": m, "created_at": now}
                                  for d, n, _, m in DEPARTMENTS])
    allocs = [{"id": "alc_org_nexora", "scope_type": "org", "scope_id": ORG_ID, "credits": ORG_BUDGET}]
    allocs += [{"id": f"alc_{d}", "scope_type": "department", "scope_id": d, "credits": c} for d, _, c, _ in DEPARTMENTS]
    allocs += [{"id": f"alc_{u[0]}", "scope_type": "user", "scope_id": u[0], "credits": u[6]} for u in ORG_USERS]
    allocs += [{"id": f"alc_{u[0]}", "scope_type": "user", "scope_id": u[0], "credits": u[4]} for u in INDIVIDUALS]
    await _upsert("allocations", [{**a, "period": "monthly", "created_at": now} for a in allocs])


async def _seed_users() -> None:
    existing = {u["id"] async for u in db.users.find({}, {"_id": 0, "id": 1})}
    demo_hash = None
    docs = []
    for uid, name, email, title, role, dept, *_rest, key in ORG_USERS:
        docs.append({"id": uid, "name": name, "email": email, "title": title, "mode": "organisation", "role": role,
                     "org_id": ORG_ID, "department_id": dept, "is_demo": key is not None, "demo_key": key})
    for uid, name, email, title, *_rest, key in INDIVIDUALS:
        docs.append({"id": uid, "name": name, "email": email, "title": title, "mode": "individual", "role": "individual",
                     "org_id": None, "department_id": None, "is_demo": key is not None, "demo_key": key})
    new = []
    for d in docs:
        if d["id"] in existing:
            if d["is_demo"]:
                demo_hash = demo_hash or hash_password(DEMO_PASSWORD)
                await db.users.update_one({"id": d["id"], "is_demo": {"$ne": True}},
                                          {"$set": {"is_demo": True, "demo_key": d["demo_key"], "password_hash": demo_hash}})
            continue
        if d["is_demo"]:
            demo_hash = demo_hash or hash_password(DEMO_PASSWORD)
            d["password_hash"] = demo_hash
        new.append({**d, "auth_provider": "password", "picture": None, "seeded": True, "created_at": now_iso()})
    await _upsert("users", new)


def _day_records(uid, org_id, dept, alloc, util, weights, day, days_ago):
    rng = random.Random(f"{uid}:{day.isoformat()}")
    if rng.random() < 0.05:
        return []
    weekday = 0.3 if day.weekday() >= 5 else 1.0
    trend = 1.0 - 0.2 * (days_ago / (USAGE_DAYS - 1))
    total = alloc * util / 21.7 * weekday * trend * rng.uniform(0.65, 1.35)
    jitter = {p: w * rng.uniform(0.6, 1.4) for p, w in weights.items()}
    norm = sum(jitter.values())
    cost = {p["id"]: p["credits_per_request"] for p in PROVIDERS}
    out = []
    for p, w in jitter.items():
        credits = round(total * w / norm)
        if credits < 3:
            continue
        out.append({"id": f"usg_{uid}_{day.isoformat()}_{p}", "user_id": uid, "org_id": org_id, "department_id": dept,
                    "provider_id": p, "date": day.isoformat(), "credits": credits,
                    "requests": max(1, round(credits / cost[p] * rng.uniform(0.8, 1.2))), "simulated": True})
    return out


async def _seed_usage() -> None:
    today = today_utc()
    meta = await db.seed_meta.find_one({"id": "usage"}, {"_id": 0})
    if meta and meta.get("through") == today.isoformat():
        return
    people = [(u[0], ORG_ID, u[5], u[6], u[7], u[8]) for u in ORG_USERS]
    people += [(u[0], None, None, u[4], u[5], u[6]) for u in INDIVIDUALS]
    records = []
    for ago in range(USAGE_DAYS):
        day = today - timedelta(days=ago)
        for p in people:
            records.extend(_day_records(*p, day, ago))
    await _upsert("usage_records", records)
    await db.seed_meta.update_one({"id": "usage"}, {"$set": {"through": today.isoformat()}}, upsert=True)
    log.info("usage seed ensured: %d records for %d days", len(records), USAGE_DAYS)


def _at(days_ago: int) -> str:
    return (now_utc() - timedelta(days=days_ago)).isoformat()


def _ledger_doc(i, initiator, lender, borrower, credits, repaid, status, note, ago, due) -> dict:
    other = lender if initiator == borrower else borrower
    hist = [{"at": _at(ago), "actor_id": initiator, "action": "requested" if initiator == borrower else "offered", "amount": credits}]
    if status in ("active", "repaid"):
        hist.append({"at": _at(max(ago - 1, 0)), "actor_id": other, "action": "accepted"})
    if status == "declined":
        hist.append({"at": _at(max(ago - 1, 0)), "actor_id": other, "action": "declined"})
    for rid, loan, amount, rstatus, rago in REPAYMENTS:
        if loan == i:
            hist.append({"at": _at(rago), "actor_id": borrower, "action": "repayment_recorded", "amount": amount})
            if rstatus == "confirmed":
                hist.append({"at": _at(max(rago - 1, 0)), "actor_id": lender, "action": "repayment_confirmed", "amount": amount})
    if status == "repaid":
        hist.append({"at": hist[-1]["at"], "actor_id": lender, "action": "repaid"})
    return {"id": i, "kind": "request" if initiator == borrower else "offer", "initiator_id": initiator,
            "lender_id": lender, "borrower_id": borrower, "credits": credits, "repaid_credits": repaid, "status": status,
            "note": note, "due_date": (today_utc() + timedelta(days=due)).isoformat() if due is not None else None,
            "created_at": _at(ago), "updated_at": hist[-1]["at"], "simulated": True, "history": hist}


async def _seed_lending() -> None:
    if not await db.seed_meta.find_one({"id": "lending_v2"}, {"_id": 1}):
        await db.lending_ledger.delete_many({"id": {"$in": [e[0] for e in LEDGER_V2]}})
        await db.lending_repayments.delete_many({"id": {"$in": [r[0] for r in REPAYMENTS]}})
        await db.seed_meta.update_one({"id": "lending_v2"}, {"$set": {"at": now_iso()}}, upsert=True)
    await _upsert("friendships", [{"id": f"frn_{a[4:]}_{b[4:]}", "pair_key": ":".join(sorted([a, b])), "requester_id": a,
                                   "addressee_id": b, "status": "accepted", "created_at": _at(ago), "responded_at": _at(ago - 1)}
                                  for a, b, ago in FRIENDSHIPS])
    await _upsert("lending_ledger", [_ledger_doc(*e) for e in LEDGER_V2])
    loans = {e[0]: e for e in LEDGER_V2}
    await _upsert("lending_repayments", [
        {"id": rid, "loan_id": loan, "borrower_id": loans[loan][3], "lender_id": loans[loan][2], "amount": amount,
         "status": rstatus, "created_at": _at(rago), "resolved_at": _at(max(rago - 1, 0)) if rstatus != "awaiting_confirmation" else None}
        for rid, loan, amount, rstatus, rago in REPAYMENTS])


async def _seed_phase3() -> None:
    """Phase 3 additions only. Existing hnd_001 / ses_001 / ses_002 records are left untouched."""
    base = today_utc()

    def at(days: int, hour: int, minute: int = 0) -> str:
        return f"{(base + timedelta(days=days)).isoformat()}T{hour:02d}:{minute:02d}:00+00:00"

    def ho(i, creator, assignee, org, title, objective, priority, done, pending, notes, status, ago, extra_hist=()):
        hist = [{"at": _at(ago), "actor_id": creator, "action": "created"}] + [
            {"at": _at(max(ago - k - 1, 0)), "actor_id": a, "action": act, **({"note": n} if n else {})} for k, (a, act, n) in enumerate(extra_hist)]
        return {"id": i, "creator_id": creator, "assignee_id": assignee, "org_id": org, "title": title, "description": "",
                "objective": objective, "priority": priority, "completed_work": done, "pending_work": pending,
                "context_notes": notes, "status": status, "created_at": _at(ago), "updated_at": hist[-1]["at"], "history": hist}

    await _upsert("handovers", [
        ho("hnd_002", "usr_arjun_mehta", "usr_noah_kim", ORG_ID, "Payments API rate-limit fix",
           "Ship the retry/backoff fix before Friday's release", "high",
           "Root cause found: burst retries from the webhook worker. Draft PR #482 adds jittered backoff.",
           "Finish load test on staging, update the runbook, request review from Sofia.",
           "Staging creds are in the team vault. Avoid running the load test during EU business hours.", "pending", 1),
        ho("hnd_003", "usr_elena_petrova", "usr_james_whitaker", ORG_ID, "Q1 onboarding research synthesis",
           "Turn 12 interview notes into 3 design opportunities", "medium",
           "Interviews done and tagged in the research board.", "Cluster insights, draft the opportunity map, share by Wednesday.",
           "Focus on the first-week drop-off segment.", "accepted", 4, [("usr_james_whitaker", "accepted", "")]),
        ho("hnd_004", "usr_maya_ellison", "usr_tomas_reyes", None, "Usability test script review",
           "Get a developer's eye on the prototype test tasks", "medium",
           "Script v2 written; 6 tasks covering checkout and saved items.", "Review tasks 3–6 for technical feasibility and flag edge cases.",
           "Prototype link is in the shared folder. Only the context in this note is shared.", "pending", 0),
        ho("hnd_005", "usr_hana_sato", "usr_maya_ellison", None, "Literature summary handoff",
           "Summarise five papers on trust in AI assistants", "low",
           "Papers selected and annotated.", "Write a one-page summary.", "Cite with APA style.", "completed", 10,
           [("usr_maya_ellison", "accepted", ""), ("usr_maya_ellison", "completed", "Summary shared as PDF.")]),
    ])

    def ses(i, user, dept, org, provider, day, hour, minutes, credits, purpose, reminder=None):
        start = at(day, hour)
        end = (datetime.fromisoformat(start) + timedelta(minutes=minutes)).isoformat(timespec="seconds")
        remind = (datetime.fromisoformat(start) - timedelta(minutes=reminder)).isoformat(timespec="seconds") if reminder else None
        return {"id": i, "user_id": user, "org_id": org, "department_id": dept, "provider_id": provider, "start_at": start, "end_at": end,
                "duration_min": minutes, "estimated_credits": credits, "purpose": purpose, "reminder_min": reminder, "remind_at": remind,
                "reminder_sent": False, "status": "planned", "suggestion": None, "created_at": now_iso(),
                "history": [{"at": now_iso(), "actor_id": user, "action": "created"}]}

    eng = "dep_engineering"
    await _upsert("sessions", [
        ses("ses_101", "usr_arjun_mehta", eng, ORG_ID, "claude", 1, 9, 90, 300, "Refactor payment retries", 30),
        ses("ses_102", "usr_arjun_mehta", eng, ORG_ID, "copilot", 3, 13, 120, 250, "Write integration tests"),
        ses("ses_103", "usr_ravi_iyer", eng, ORG_ID, "gemini", 2, 10, 60, 400, "Embedding eval batch run", 15),
        ses("ses_104", "usr_chloe_martin", eng, ORG_ID, "copilot", 4, 14, 60, 120, "Component library cleanup"),
        ses("ses_105", "usr_oliver_grant", "dep_marketing", ORG_ID, "chatgpt", 2, 15, 90, 350, "Q1 campaign copy drafts", 30),
        ses("ses_106", "usr_maya_ellison", None, None, "claude", 1, 14, 60, 120, "Interview synthesis round 2", 30),
        ses("ses_107", "usr_maya_ellison", None, None, "perplexity", 4, 10, 45, 60, "Competitor research"),
        ses("ses_108", "usr_tomas_reyes", None, None, "copilot", 2, 16, 120, 200, "Client sprint: checkout API"),
    ])


async def _seed_activity() -> None:
    await _seed_lending()
    await _seed_phase3()
    await db.resource_requests.update_many({"urgency": {"$exists": False}}, {"$set": {"urgency": "normal", "history": []}})
    await db.resource_requests.update_one({"id": "req_001", "urgency": "normal", "history": []}, {"$set": {"urgency": "high"}})
    await _upsert("resource_requests", [
        {"id": "req_001", "org_id": ORG_ID, "requester_id": "usr_arjun_mehta", "department_id": "dep_engineering",
         "credits": 1000, "reason": "Payment service refactor needs extra Claude capacity", "status": "pending",
         "urgency": "high", "history": [], "created_at": _ago(1)},
        {"id": "req_002", "org_id": ORG_ID, "requester_id": "usr_oliver_grant", "department_id": "dep_marketing",
         "credits": 600, "reason": "Q4 campaign content production", "status": "approved", "approved_credits": 600,
         "urgency": "normal", "history": [], "created_at": _ago(12)},
    ])
    await _upsert("handovers", [
        {"id": "hnd_001", "org_id": ORG_ID, "from_user_id": "usr_ravi_iyer", "to_user_id": "usr_arjun_mehta",
         "title": "Embedding pipeline evaluation", "status": "in_progress", "created_at": _ago(3)},
    ])
    await _upsert("sessions", [
        {"id": "ses_001", "user_id": "usr_arjun_mehta", "title": "API migration deep work", "provider_id": "claude",
         "estimated_credits": 400, "start_at": _ago(-1), "status": "planned"},
        {"id": "ses_002", "user_id": "usr_maya_ellison", "title": "Interview synthesis", "provider_id": "chatgpt",
         "estimated_credits": 250, "start_at": _ago(-2), "status": "planned"},
    ])
    await _upsert("notifications", [
        {"id": "ntf_001", "user_id": "usr_sofia_marchetti", "type": "resource_request", "title": "Arjun Mehta requested 1,000 credits",
         "read": False, "created_at": _ago(1)},
        {"id": "ntf_002", "user_id": "usr_maya_ellison", "type": "lending", "title": "Kwame Boateng asked to borrow 200 credits",
         "read": False, "created_at": _ago(2)},
    ])


async def run_seed() -> None:
    await _seed_core()
    await _seed_users()
    await _seed_usage()
    await _seed_activity()
    await _seed_tasks()
    log.info("seed complete")


DEMO_GOALS = [
    # (goal id, owner, title, description, priority, days to deadline, {subtask index: (assignee, status)})
    ("goal_demo_payments", "usr_sofia_marchetti", "Ship the payments API v2 retry logic",
     "Add idempotent retries to the payments API, with tests and a rollout note for the support team.", "high", 10,
     {0: ("usr_sofia_marchetti", "done"), 1: ("usr_arjun_mehta", "in_progress"), 2: ("usr_arjun_mehta", "todo")}),
    ("goal_demo_research", "usr_maya_ellison", "Research onboarding drop-off for a fintech app",
     "Compare onboarding flows of three competitors and summarise why users drop off in week one.", "medium", 14,
     {0: ("usr_maya_ellison", "todo")}),
]


async def _seed_tasks() -> None:
    """Two demo goals created through the same rules engine users get. Idempotent: never overwrites edits."""
    from services.decompose import rules_decompose, validate_graph
    from core.db import now_iso as _now
    from datetime import timedelta as _td
    for goal_id, owner_id, title, desc, priority, days, assigned in DEMO_GOALS:
        if await db.tasks.find_one({"id": goal_id}, {"_id": 1}):
            continue
        owner = await db.users.find_one({"id": owner_id}, {"_id": 0, "id": 1, "org_id": 1, "department_id": 1, "mode": 1})
        if not owner:
            continue
        plan = rules_decompose(title, desc, priority)["subtasks"]
        waves = validate_graph(plan)
        now = _now()
        deadline = (datetime.now(timezone.utc) + _td(days=days)).replace(hour=17, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        ids = [f"{goal_id}_t{i + 1}" for i in range(len(plan))]
        base = {"owner_id": owner_id, "org_id": owner.get("org_id"), "department_id": owner.get("department_id")}
        await db.tasks.insert_one({"id": goal_id, "kind": "goal", "root_id": goal_id, "parent_id": None, **base, "mode": owner["mode"],
                                   "title": title, "description": desc, "priority": priority, "deadline": deadline, "status": "open",
                                   "method": "rules", "summary": "", "created_at": now, "updated_at": now,
                                   "history": [{"at": now, "actor_id": owner_id, "action": "created"}]})
        docs = []
        for i, st in enumerate(plan):
            who, status = assigned.get(i, (None, "todo"))
            docs.append({"id": ids[i], "kind": "subtask", "root_id": goal_id, "parent_id": goal_id, "order": i, **base,
                         "title": st["title"], "description": "", "type": st["type"], "depends_on": [ids[d] for d in st["depends_on"]],
                         "wave": waves[i], "priority": priority, "deadline": deadline, "status": status,
                         "estimate": {"low": st["estimate_low"], "high": st["estimate_high"], "basis": "rules",
                                      "provenance": "Estimated by Orqestra's built-in rules"},
                         "provider_id": st["provider_id"], "tool_reason": st["tool_reason"], "assignee_id": who,
                         "assignment": {"by": owner_id, "at": now, "reason": "Seed data"} if who else None,
                         "session_id": None, "suggested_slot": None,
                         "output": {"summary": "Requirements and acceptance criteria agreed with support.", "by": who, "at": now} if status == "done" else None,
                         "created_at": now, "updated_at": now, "history": [{"at": now, "actor_id": owner_id, "action": "created"}]})
        await db.tasks.insert_many(docs)
