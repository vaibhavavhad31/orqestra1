"""Tasks: the central record linking goals, sub-tasks, people, AI tools, credits and planner sessions."""
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from core.db import db, new_id, now_iso, now_utc
from services.actions import history, notify
from services.decompose import TOOL_RULES, TYPES, validate_graph
from services.lending import balances, is_friend
from services import planner
from services.usage import allocation_map, usage_rows, window
from services.users import audit
from services.validation import field_error

P = {"_id": 0}
PRIORITIES = ("low", "medium", "high", "urgent")
SUB_STATUSES = ("todo", "in_progress", "blocked", "done")
CREDITS_PER_HOUR = 200  # planning heuristic for session length, shown as an estimate
WORK_START, WORK_END = 9, 18  # local working hours for slot suggestions
PROVENANCE = {
    "estimate_rules": "Estimated by Orqestra's built-in rules",
    "estimate_ai": "Estimated by your LLM",
    "estimate_manual": "Entered by a person",
    "capacity_org": "Orqestra budget record minus simulated usage",
    "capacity_personal": "Personal capacity record minus simulated usage",
    "usage": "Simulated usage data",
    "reset": "Reset time entered by the user",
}


# ---------- access ----------

async def _users(ids) -> dict:
    return {u["id"]: u async for u in db.users.find({"id": {"$in": list(ids)}},
                                                     {"_id": 0, "id": 1, "name": 1, "department_id": 1, "role": 1, "mode": 1, "org_id": 1, "title": 1})}


async def can_view_goal(user: dict, goal: dict, subtasks: list[dict]) -> bool:
    if user["id"] == goal["owner_id"] or any(s.get("assignee_id") == user["id"] for s in subtasks):
        return True
    if user["mode"] != "organisation" or goal.get("org_id") != user.get("org_id"):
        return False
    if user["role"] == "admin":
        return True
    return user["role"] == "manager" and goal.get("department_id") == user.get("department_id")


def can_manage(user: dict, goal: dict) -> bool:
    if user["id"] == goal["owner_id"]:
        return True
    if user["mode"] == "organisation" and goal.get("org_id") == user.get("org_id"):
        return user["role"] == "admin" or (user["role"] == "manager" and goal.get("department_id") == user.get("department_id"))
    return False


async def _load_goal(user: dict, goal_id: str) -> tuple[dict, list[dict]]:
    goal = await db.tasks.find_one({"id": goal_id, "kind": "goal"}, P)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    subs = await db.tasks.find({"root_id": goal_id, "kind": "subtask"}, P).sort("order", 1).to_list(100)
    if not await can_view_goal(user, goal, subs):
        raise HTTPException(status_code=403, detail="You don't have access to this goal")
    return goal, subs


async def _load_subtask(user: dict, task_id: str) -> tuple[dict, dict, list[dict]]:
    sub = await db.tasks.find_one({"id": task_id, "kind": "subtask"}, P)
    if not sub:
        raise HTTPException(status_code=404, detail="Sub-task not found")
    goal, subs = await _load_goal(user, sub["root_id"])
    return sub, goal, subs


async def candidate_pool(user: dict) -> list[dict]:
    """People a task in this workspace can be assigned to (same rules as handovers, plus yourself)."""
    if user["mode"] == "individual":
        ids = [user["id"]]
        async for f in db.friendships.find({"status": "accepted", "$or": [{"requester_id": user["id"]}, {"addressee_id": user["id"]}]}, P):
            ids.append(f["addressee_id"] if f["requester_id"] == user["id"] else f["requester_id"])
        q = {"id": {"$in": ids}}
    else:
        q = {"org_id": user["org_id"]}
    q["status"] = {"$ne": "deactivated"}
    return await db.users.find(q, {"_id": 0, "id": 1, "name": 1, "title": 1, "department_id": 1, "role": 1, "mode": 1}).sort("name", 1).to_list(500)


async def _check_assignable(user: dict, assignee_id: str) -> dict:
    pool = {u["id"]: u for u in await candidate_pool(user)}
    if assignee_id not in pool:
        raise field_error(400, {"assignee_id": "You can't assign work to this person"})
    return pool[assignee_id]


# ---------- serialisation ----------

async def _provider_names() -> dict:
    return {p["id"]: p["name"] async for p in db.providers.find({}, {"_id": 0, "id": 1, "name": 1})}


def _progress(subs: list[dict]) -> dict:
    done = sum(1 for s in subs if s["status"] == "done")
    return {"done": done, "total": len(subs), "pct": round(done / len(subs) * 100) if subs else 0}


def _blocked_by(sub: dict, by_id: dict) -> list[str]:
    return [d for d in sub.get("depends_on", []) if by_id.get(d, {}).get("status") != "done"]


async def serialize_goal(user: dict, goal: dict, subs: list[dict], detail: bool = False) -> dict:
    names = await _users({goal["owner_id"]} | {s["assignee_id"] for s in subs if s.get("assignee_id")})
    providers = await _provider_names()
    by_id = {s["id"]: s for s in subs}
    out = {**{k: v for k, v in goal.items() if k != "history"}, "owner_name": names.get(goal["owner_id"], {}).get("name"),
           "progress": _progress(subs), "waves": (max((s["wave"] for s in subs), default=-1) + 1),
           "estimate_low": sum(s["estimate"]["low"] for s in subs), "estimate_high": sum(s["estimate"]["high"] for s in subs),
           "unassigned": sum(1 for s in subs if not s.get("assignee_id")),
           "ready_to_consolidate": bool(subs) and all(s["status"] == "done" for s in subs) and goal["status"] != "done",
           "can_manage": can_manage(user, goal)}
    if detail:
        out["history"] = goal.get("history", [])
        out["subtasks"] = [{**s, "assignee_name": names.get(s.get("assignee_id"), {}).get("name"),
                            "provider_name": providers.get(s.get("provider_id")),
                            "dependency_titles": [by_id[d]["title"] for d in s.get("depends_on", []) if d in by_id],
                            "blocked_by": _blocked_by(s, by_id),
                            "can_update": s.get("assignee_id") == user["id"] or out["can_manage"],
                            "can_schedule": s.get("assignee_id") == user["id"]}
                           for s in subs]
        out["provenance"] = PROVENANCE
    return out


# ---------- goals ----------

async def list_goals(user: dict, scope: str) -> list[dict]:
    if scope == "team":
        if user["mode"] != "organisation" or user["role"] not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Only Managers and Admins can see team goals")
        q = {"kind": "goal", "org_id": user["org_id"], **({"department_id": user["department_id"]} if user["role"] == "manager" else {})}
        goals = await db.tasks.find(q, P).sort("created_at", -1).to_list(300)
    else:
        assigned_roots = {s["root_id"] async for s in db.tasks.find({"kind": "subtask", "assignee_id": user["id"]}, {"_id": 0, "root_id": 1})}
        goals = await db.tasks.find({"kind": "goal", "$or": [{"owner_id": user["id"]}, {"id": {"$in": list(assigned_roots)}}]}, P) \
            .sort("created_at", -1).to_list(300)
    out = []
    for g in goals:
        subs = await db.tasks.find({"root_id": g["id"], "kind": "subtask"}, P).to_list(100)
        item = await serialize_goal(user, g, subs)
        item["my_open"] = sum(1 for s in subs if s.get("assignee_id") == user["id"] and s["status"] != "done")
        out.append(item)
    return out


async def get_goal(user: dict, goal_id: str) -> dict:
    goal, subs = await _load_goal(user, goal_id)
    return await serialize_goal(user, goal, subs, detail=True)


def _parse_deadline(value) -> str | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise field_error(422, {"deadline": "Enter a valid deadline"})
    d = d if d.tzinfo else d.replace(hour=18 if len(str(value)) <= 10 else d.hour, tzinfo=timezone.utc)
    if d < now_utc() - timedelta(days=1):
        raise field_error(422, {"deadline": "The deadline can't be in the past"})
    return d.astimezone(timezone.utc).isoformat(timespec="seconds")


async def create_goal(user: dict, body: dict) -> dict:
    title = (body.get("title") or "").strip()
    errors = {}
    if not title:
        errors["title"] = "Add a goal title"
    priority = body.get("priority") or "medium"
    if priority not in PRIORITIES:
        errors["priority"] = "Choose low, medium, high or urgent"
    if errors:
        raise field_error(422, errors)
    deadline = _parse_deadline(body.get("deadline"))
    raw = body.get("subtasks") or []
    providers = await _provider_names()
    clean = []
    for i, s in enumerate(raw):
        typ = s.get("type") if s.get("type") in TYPES else "planning"
        try:
            low, high = int(s.get("estimate_low") or 0), int(s.get("estimate_high") or 0)
        except (TypeError, ValueError):
            raise field_error(422, {"subtasks": f"Sub-task {i + 1} needs whole-number estimates"})
        if low < 1 or high < low:
            raise field_error(422, {"subtasks": f"Sub-task {i + 1}: estimates must be at least 1 and low ≤ high"})
        provider_id = s.get("provider_id") if s.get("provider_id") in providers else TOOL_RULES[typ][0]
        clean.append({"title": (s.get("title") or "").strip()[:160], "description": (s.get("description") or "").strip()[:1000],
                      "type": typ, "depends_on": [d for d in (s.get("depends_on") or []) if isinstance(d, int)],
                      "low": low, "high": high, "provider_id": provider_id,
                      "tool_reason": (s.get("tool_reason") or TOOL_RULES[typ][1])[:200],
                      "basis": s.get("basis") if s.get("basis") in ("rules", "ai", "manual") else "manual"})
    waves = validate_graph([{"title": c["title"], "depends_on": c["depends_on"]} for c in clean])
    now = now_iso()
    goal_id = new_id("goal")
    goal = {"id": goal_id, "kind": "goal", "root_id": goal_id, "parent_id": None, "owner_id": user["id"],
            "org_id": user.get("org_id"), "department_id": user.get("department_id"), "mode": user["mode"],
            "title": title[:160], "description": (body.get("description") or "").strip()[:2000], "priority": priority,
            "deadline": deadline, "status": "open", "method": body.get("method") if body.get("method") in ("rules", "ai", "manual") else "manual",
            "summary": "", "created_at": now, "updated_at": now, "history": [history(user["id"], "created")]}
    ids = [new_id("tsk") for _ in clean]
    docs = []
    for i, c in enumerate(clean):
        docs.append({"id": ids[i], "kind": "subtask", "root_id": goal_id, "parent_id": goal_id, "order": i,
                     "owner_id": user["id"], "org_id": user.get("org_id"), "department_id": user.get("department_id"),
                     "title": c["title"], "description": c["description"], "type": c["type"],
                     "depends_on": [ids[d] for d in c["depends_on"]], "wave": waves[i], "priority": priority,
                     "deadline": deadline, "status": "todo",
                     "estimate": {"low": c["low"], "high": c["high"], "basis": c["basis"],
                                  "provenance": PROVENANCE[f"estimate_{c['basis']}"]},
                     "provider_id": c["provider_id"], "tool_reason": c["tool_reason"], "assignee_id": None,
                     "assignment": None, "session_id": None, "suggested_slot": None, "output": None,
                     "created_at": now, "updated_at": now, "history": [history(user["id"], "created")]})
    await db.tasks.insert_one(goal)
    if docs:
        await db.tasks.insert_many(docs)
    await audit(user["id"], "task.goal_created", {"goal_id": goal_id, "subtasks": len(docs), "method": goal["method"]})
    return await get_goal(user, goal_id)


async def update_goal(user: dict, goal_id: str, body: dict) -> dict:
    goal, subs = await _load_goal(user, goal_id)
    if not can_manage(user, goal):
        raise HTTPException(status_code=403, detail="Only the goal owner, or their Manager or Admin, can change this goal")
    updates: dict = {}
    if body.get("status") == "done":
        if subs and any(s["status"] != "done" for s in subs):
            raise HTTPException(status_code=409, detail="Finish every sub-task before closing the goal")
        updates["status"] = "done"
        updates["summary"] = (body.get("summary") or "").strip()[:4000] or _auto_summary(subs)
    elif body.get("status") == "open":
        updates["status"] = "open"
    if updates:
        await db.tasks.update_one({"id": goal_id}, {"$set": {**updates, "updated_at": now_iso()},
                                                    "$push": {"history": history(user["id"], f"goal_{updates.get('status', 'edited')}")}})
    return await get_goal(user, goal_id)


def _auto_summary(subs: list[dict]) -> str:
    lines = []
    for s in sorted(subs, key=lambda x: (x["wave"], x["order"])):
        out = (s.get("output") or {}).get("summary") or "Done (no output summary given)"
        lines.append(f"- {s['title']}: {out}")
    return "\n".join(lines)


async def delete_goal(user: dict, goal_id: str) -> dict:
    goal, subs = await _load_goal(user, goal_id)
    if not can_manage(user, goal):
        raise HTTPException(status_code=403, detail="Only the goal owner, or their Manager or Admin, can delete this goal")
    await db.tasks.delete_many({"root_id": goal_id})
    await audit(user["id"], "task.goal_deleted", {"goal_id": goal_id})
    return {"ok": True}


# ---------- sub-tasks ----------

async def update_subtask(user: dict, task_id: str, body: dict) -> dict:
    sub, goal, subs = await _load_subtask(user, task_id)
    manager = can_manage(user, goal)
    is_assignee = sub.get("assignee_id") == user["id"]
    if not (manager or is_assignee):
        raise HTTPException(status_code=403, detail="Only the assignee or the goal owner can update this sub-task")
    updates: dict = {}
    entries = []
    if "assignee_id" in body:
        if not manager:
            raise HTTPException(status_code=403, detail="Only the goal owner, or their Manager or Admin, can assign work")
        new = body.get("assignee_id") or None
        if new:
            person = await _check_assignable(user, new)
            updates["assignee_id"] = new
            updates["assignment"] = {"by": user["id"], "at": now_iso(), "reason": (body.get("assignment_reason") or "").strip()[:300]}
            updates["session_id"] = None
            updates["suggested_slot"] = None
            entries.append(history(user["id"], "assigned", note=person["name"]))
        else:
            updates["assignee_id"] = None
            updates["assignment"] = None
            entries.append(history(user["id"], "unassigned"))
    if "status" in body:
        status = body.get("status")
        if status not in SUB_STATUSES:
            raise field_error(422, {"status": "Choose to do, in progress, blocked or done"})
        if status in ("in_progress", "done"):
            by_id = {s["id"]: s for s in subs}
            pending = _blocked_by(sub, by_id)
            if pending and status == "in_progress":
                titles = ", ".join(by_id[d]["title"] for d in pending)
                raise HTTPException(status_code=409, detail=f"Waiting on: {titles}")
        updates["status"] = status
        if status == "done":
            updates["output"] = {"summary": (body.get("output_summary") or "").strip()[:2000], "by": user["id"], "at": now_iso()}
        entries.append(history(user["id"], status))
    if "title" in body and manager:
        t = (body.get("title") or "").strip()
        if not t:
            raise field_error(422, {"title": "Add a title"})
        updates["title"] = t[:160]
    if "estimate_low" in body or "estimate_high" in body:
        if not manager:
            raise HTTPException(status_code=403, detail="Only the goal owner can change estimates")
        try:
            low, high = int(body.get("estimate_low", sub["estimate"]["low"])), int(body.get("estimate_high", sub["estimate"]["high"]))
        except (TypeError, ValueError):
            raise field_error(422, {"estimate": "Use whole numbers"})
        if low < 1 or high < low:
            raise field_error(422, {"estimate": "Estimates must be at least 1 and low ≤ high"})
        updates["estimate"] = {"low": low, "high": high, "basis": "manual", "provenance": PROVENANCE["estimate_manual"]}
    if "provider_id" in body and manager:
        if body["provider_id"] not in await _provider_names():
            raise field_error(422, {"provider_id": "Choose a tool"})
        updates["provider_id"] = body["provider_id"]
        updates["tool_reason"] = "Chosen by the goal owner"
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    push = {"$push": {"history": {"$each": entries}}} if entries else {}
    await db.tasks.update_one({"id": task_id}, {"$set": {**updates, "updated_at": now_iso()}, **push})
    if updates.get("assignee_id") and updates["assignee_id"] != user["id"]:
        await notify(updates["assignee_id"], "task.assigned", f"{user['name']} assigned you “{sub['title']}”", {"goal_id": goal["id"], "task_id": task_id})
    if updates.get("status") == "done" and goal["owner_id"] != user["id"]:
        await notify(goal["owner_id"], "task.done", f"{user['name']} finished “{sub['title']}”", {"goal_id": goal["id"], "task_id": task_id})
    await audit(user["id"], "task.updated", {"task_id": task_id, "fields": sorted(updates)})
    return await get_goal(user, goal["id"])


# ---------- resource allocation ----------

async def _capacity(person: dict) -> tuple[int, str]:
    if person["mode"] == "individual":
        _, b = await balances(person["id"])
        return int(b["available"]), PROVENANCE["capacity_personal"]
    alloc = (await allocation_map("user", [person["id"]])).get(person["id"], 0)
    used = sum(r["credits"] for r in await usage_rows({"user_id": person["id"]}, window(30)))
    return int(alloc - used), PROVENANCE["capacity_org"]


async def _tool_share(person_id: str, provider_id: str) -> float:
    rows = await usage_rows({"user_id": person_id}, window(30))
    total = sum(r["credits"] for r in rows)
    on_tool = sum(r["credits"] for r in rows if r.get("provider_id") == provider_id)
    return on_tool / total if total else 0.0


async def _load(person_id: str) -> tuple[int, int]:
    open_tasks = await db.tasks.count_documents({"kind": "subtask", "assignee_id": person_id, "status": {"$ne": "done"}})
    now = now_utc()
    week = [s for s in await planner._own_sessions(person_id)
            if s["status"] == "planned" and planner._iso(now) <= s["start_at"] <= planner._iso(now + timedelta(days=7))]
    return open_tasks, len(week)


def _may_see_numbers(viewer: dict, person: dict) -> bool:
    if viewer["id"] == person["id"] or viewer["mode"] == "individual":
        return True
    return viewer["role"] == "admin" or (viewer["role"] == "manager" and viewer.get("department_id") == person.get("department_id"))


async def candidates(user: dict, task_id: str) -> dict:
    sub, goal, _ = await _load_subtask(user, task_id)
    if not can_manage(user, goal):
        raise HTTPException(status_code=403, detail="Only the goal owner, or their Manager or Admin, can assign work")
    low, high = sub["estimate"]["low"], sub["estimate"]["high"]
    providers = await _provider_names()
    tool = providers.get(sub["provider_id"], sub["provider_id"])
    ranked = []
    for person in await candidate_pool(user):
        headroom, cap_source = await _capacity(person)
        share = await _tool_share(person["id"], sub["provider_id"])
        open_tasks, sessions = await _load(person["id"])
        fits = headroom >= high
        partly = headroom >= low
        same_team = bool(goal.get("department_id")) and person.get("department_id") == goal.get("department_id")
        # 45 capacity (full marks at 3x the high estimate) + 25 tool experience + 20 free time + 10 same team
        score = 45 * min(max(headroom, 0) / (high * 3), 1.0) + 25 * min(share / 0.5, 1.0) \
            + 20 * (1 - min((open_tasks + sessions) / 6, 1.0)) + (10 if same_team else 0) - (0 if fits else 15 if partly else 40)
        numbers = _may_see_numbers(user, person)
        if numbers:
            cap_text = f"{max(headroom, 0):,} credits free (needs ~{low:,}–{high:,})"
        else:
            cap_text = "enough capacity for this" if fits else "may be short on capacity" if partly else "low on capacity"
        reasons = [cap_text, f"uses {tool} for {round(share * 100)}% of their work" if share else f"hasn't used {tool} recently",
                   f"{open_tasks} open task{'s' if open_tasks != 1 else ''}, {sessions} session{'s' if sessions != 1 else ''} this week"]
        if same_team:
            reasons.append("same department as the goal owner")
        ranked.append({"user_id": person["id"], "name": person["name"], "title": person.get("title"),
                       "score": max(0, round(score)), "fits": fits, "partly_fits": partly and not fits,
                       "headroom": headroom if numbers else None, "tool_share_pct": round(share * 100),
                       "open_tasks": open_tasks, "sessions_this_week": sessions, "reason": "; ".join(reasons),
                       "is_current": sub.get("assignee_id") == person["id"], "is_you": person["id"] == user["id"]})
    ranked.sort(key=lambda c: (-c["score"], c["name"]))
    needs_capacity = not any(c["fits"] or c["partly_fits"] for c in ranked)
    return {"task_id": task_id, "tool": tool, "estimate": sub["estimate"], "candidates": ranked[:3], "all": ranked,
            "needs_capacity": needs_capacity,
            "provenance": {"capacity": PROVENANCE["capacity_org"] if user["mode"] == "organisation" else PROVENANCE["capacity_personal"],
                           "usage": PROVENANCE["usage"], "estimate": sub["estimate"]["provenance"]},
            "capacity_options": _capacity_options(user)}


def _capacity_options(user: dict) -> list[dict]:
    """What to do when nobody has capacity. Never a provider quota transfer."""
    if user["mode"] == "organisation":
        return [{"kind": "request_budget", "label": "Request more internal budget", "link": "/allocation",
                 "note": "Internal budget only. Provider limits are not changed."},
                {"kind": "reallocate", "label": "Reallocate from an underused teammate", "link": "/allocation",
                 "note": "Managers and Admins move internal budget between people."},
                {"kind": "handover", "label": "Hand the work to a teammate", "link": "/handover",
                 "note": "They do the work in their own AI account."}]
    return [{"kind": "handover", "label": "Ask a friend to take this work", "link": "/handover",
             "note": "They do the work in their own account. No credits or logins are shared."}]


# ---------- planner slot suggestions ----------

def _ceil_to(dt: datetime, minutes: int) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    extra = (-dt.minute) % minutes
    return dt + timedelta(minutes=extra)


def _duration_min(high: int) -> int:
    minutes = round(high / CREDITS_PER_HOUR * 60 / 15) * 15
    return max(30, min(180, minutes))


async def suggest_slot(user: dict, task_id: str, tz_offset_min: int = 0) -> dict:
    sub, goal, subs = await _load_subtask(user, task_id)
    assignee_id = sub.get("assignee_id")
    if not assignee_id:
        raise HTTPException(status_code=409, detail="Assign this sub-task first, so Orqestra knows whose calendar to use")
    if not (assignee_id == user["id"] or can_manage(user, goal)):
        raise HTTPException(status_code=403, detail="Only the assignee or the goal owner can plan this sub-task")
    tz = timezone(timedelta(minutes=-int(tz_offset_min)))  # JS getTimezoneOffset(): minutes behind UTC
    duration = timedelta(minutes=_duration_min(sub["estimate"]["high"]))
    reasons = [f"{int(duration.total_seconds() // 60)} min, sized from the high estimate ({sub['estimate']['high']:,} credits at ~{CREDITS_PER_HOUR}/hour)"]
    warnings: list[str] = []
    earliest = _ceil_to(now_utc() + timedelta(minutes=15), 30)
    by_id = {s["id"]: s for s in subs}
    sessions_by_id = {s["id"]: s for s in await planner._own_sessions(assignee_id)}
    for dep_id in sub.get("depends_on", []):
        dep = by_id.get(dep_id)
        if not dep or dep["status"] == "done":
            continue
        dep_session = None
        if dep.get("session_id"):
            dep_session = await db.sessions.find_one({"id": dep["session_id"]}, P)
        if dep_session and dep_session.get("status") == "planned":
            end = planner._dt(planner.norm(dep_session)["end_at"]) + timedelta(minutes=30)
            if end > earliest:
                earliest = _ceil_to(end, 30)
            reasons.append(f"Starts after “{dep['title']}” is planned to finish")
        else:
            warnings.append(f"“{dep['title']}” isn't finished or scheduled yet. Plan it first, or this slot may be too early.")
    reset = await db.provider_resets.find_one({"user_id": assignee_id, "provider_id": sub["provider_id"]}, P)
    if reset and reset.get("next_reset_at") and sub["estimate"]["high"] >= 300:
        reset_at = planner._dt(reset["next_reset_at"])
        if reset_at and earliest < reset_at < earliest + timedelta(days=2):
            earliest = _ceil_to(reset_at, 15)
            reasons.append(f"Heavy session, so it starts after the {reset.get('reset_type')} reset the user entered")
    busy = sorted([(planner._dt(s["start_at"]), planner._dt(s["end_at"])) for s in sessions_by_id.values() if s["status"] == "planned"])
    start = earliest
    for _ in range(24 * 21):  # look up to three weeks ahead in 30-minute steps (bounded loop)
        local = start.astimezone(tz)
        day_start = local.replace(hour=WORK_START, minute=0)
        day_end = local.replace(hour=WORK_END, minute=0)
        if local.weekday() >= 5 or local >= day_end:
            nxt = (local + timedelta(days=1)).replace(hour=WORK_START, minute=0)
            start = nxt.astimezone(timezone.utc)
            continue
        if local < day_start:
            start = day_start.astimezone(timezone.utc)
            continue
        end = start + duration
        if end.astimezone(tz) > day_end:
            start = (local + timedelta(days=1)).replace(hour=WORK_START, minute=0).astimezone(timezone.utc)
            continue
        clash = next(((b0, b1) for b0, b1 in busy if b0 < end and start < b1), None)
        if clash:
            start = _ceil_to(clash[1], 15)
            continue
        break
    else:
        raise HTTPException(status_code=409, detail="No free slot in the next three weeks of working hours")
    end = start + duration
    reasons.append("First free slot in working hours (09:00–18:00, weekdays) with no overlap in the assignee's planner")
    deadline = planner._dt(sub.get("deadline")) if sub.get("deadline") else None
    if deadline and end > deadline:
        warnings.append("This slot ends after the deadline. Consider reassigning, switching tool or moving the deadline.")
    providers = await _provider_names()
    return {"task_id": task_id, "assignee_id": assignee_id, "start_at": planner._iso(start), "end_at": planner._iso(end),
            "provider_id": sub["provider_id"], "provider_name": providers.get(sub["provider_id"]),
            "estimated_credits": sub["estimate"]["high"], "reasons": reasons, "warnings": warnings,
            "provenance": {"estimate": sub["estimate"]["provenance"],
                           "availability": "Working hours assumed 09:00–18:00 on weekdays; existing planner sessions",
                           "reset": PROVENANCE["reset"] if reset else "No reset time entered (unavailable)"}}


async def schedule(user: dict, task_id: str, body: dict) -> dict:
    sub, goal, _ = await _load_subtask(user, task_id)
    slot = {"start_at": body.get("start_at"), "end_at": body.get("end_at"), "provider_id": body.get("provider_id") or sub["provider_id"]}
    if sub.get("assignee_id") == user["id"]:
        res = await planner.create(user, {**slot, "estimated_credits": sub["estimate"]["high"],
                                          "purpose": sub["title"][:200], "reminder_min": 15})
        session_id = res["session"]["id"]
        await db.sessions.update_one({"id": session_id}, {"$set": {"task_id": task_id, "goal_id": goal["id"]}})
        await db.tasks.update_one({"id": task_id}, {"$set": {"session_id": session_id, "suggested_slot": None, "updated_at": now_iso()},
                                                     "$push": {"history": history(user["id"], "scheduled", note=slot["start_at"])}})
        return {"scheduled": True, "session": res["session"], "warning": res.get("warning"), "goal": await get_goal(user, goal["id"])}
    if not can_manage(user, goal) or not sub.get("assignee_id"):
        raise HTTPException(status_code=403, detail="Only the assignee can add this to their planner")
    if not planner._dt(slot["start_at"]) or not planner._dt(slot["end_at"]):
        raise field_error(422, {"start_at": "Enter a valid time"})
    sug = {**slot, "by": user["id"], "by_name": user["name"], "at": now_iso()}
    await db.tasks.update_one({"id": task_id}, {"$set": {"suggested_slot": sug, "updated_at": now_iso()},
                                                 "$push": {"history": history(user["id"], "slot_suggested", note=slot["start_at"])}})
    await notify(sub["assignee_id"], "task.slot", f"{user['name']} suggested a time for “{sub['title']}”", {"goal_id": goal["id"], "task_id": task_id})
    return {"scheduled": False, "suggested": True, "goal": await get_goal(user, goal["id"])}
