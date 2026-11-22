from fastapi import HTTPException
from pymongo import ReturnDocument
from core.db import db, new_id, now_iso, today_utc
from core.locks import locked
from services.actions import parse_credits, parse_due_date, bad_request, conflict, history, notify
from services.usage import window, usage_rows, total, allocation_map
from services.users import audit
from services.validation import field_error

DISCLAIMER = "Obligation tracking only. No provider credits are transferred."
NOT_ENOUGH = "Not enough available credits to lend"
P = {"_id": 0}


def outstanding(e: dict) -> int:
    return e["credits"] - e.get("repaid_credits", 0) if e["status"] == "active" else 0


def is_overdue(e: dict) -> bool:
    return e["status"] == "active" and bool(e.get("due_date")) and e["due_date"] < today_utc().isoformat()


async def entries_for(uid: str) -> list[dict]:
    q = {"$or": [{"lender_id": uid}, {"borrower_id": uid}]}
    return await db.lending_ledger.find(q, P).sort("created_at", -1).to_list(2000)


async def balances(uid: str) -> tuple[list[dict], dict]:
    """available = capacity − own usage (30-day cycle) − lent outstanding + borrowed outstanding (REQ-24)."""
    entries = await entries_for(uid)
    lent = sum(outstanding(e) for e in entries if e["lender_id"] == uid)
    borrowed = sum(outstanding(e) for e in entries if e["borrower_id"] == uid)
    capacity = (await allocation_map("user", [uid])).get(uid, 0)
    used = total(await usage_rows({"user_id": uid}, window(30)))
    return entries, {"capacity": capacity, "used": used, "lent_outstanding": lent, "borrowed_outstanding": borrowed,
                     "net": lent - borrowed, "available": capacity - used - lent + borrowed}


async def summary(uid: str) -> dict:
    entries, b = await balances(uid)
    awaiting = await db.lending_repayments.count_documents({"lender_id": uid, "status": "awaiting_confirmation"})
    needs = sum(1 for e in entries if e["status"] == "pending" and e.get("initiator_id") != uid)
    return {**b, "active_loans": sum(1 for e in entries if e["status"] == "active"),
            "pending_requests": sum(1 for e in entries if e["status"] == "pending"),
            "pending_actions": needs + awaiting, "overdue": sum(1 for e in entries if is_overdue(e)),
            "simulated_disclaimer": DISCLAIMER}


async def _names(ids) -> dict:
    return {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1})}


def serialize(e: dict, uid: str, names: dict, reps: list[dict]) -> dict:
    lent = e["lender_id"] == uid
    other = e["borrower_id"] if lent else e["lender_id"]
    awaiting = sum(r["amount"] for r in reps if r["status"] == "awaiting_confirmation")
    theirs = e["status"] == "pending" and e.get("initiator_id") != uid
    mine = e["status"] == "pending" and e.get("initiator_id") == uid
    owed = outstanding(e)
    return {**e, "direction": "lent" if lent else "borrowed", "my_role": "lender" if lent else "borrower",
            "counterparty_id": other, "counterparty_name": names.get(other), "outstanding": owed,
            "awaiting_repayment": awaiting, "overdue": is_overdue(e),
            "needs_my_action": theirs or (lent and awaiting > 0),
            "actions": {"accept": theirs, "decline": theirs, "cancel": mine,
                        "repay": (not lent) and e["status"] == "active" and owed - awaiting > 0}}


async def list_entries(uid: str, tab: str = "all") -> list[dict]:
    entries = await entries_for(uid)
    reps = await db.lending_repayments.find({"loan_id": {"$in": [e["id"] for e in entries]}}, P).to_list(5000)
    by_loan: dict = {}
    for r in reps:
        by_loan.setdefault(r["loan_id"], []).append(r)
    names = await _names({e["lender_id"] for e in entries} | {e["borrower_id"] for e in entries})
    out = [serialize(e, uid, names, by_loan.get(e["id"], [])) for e in entries]
    if tab == "borrowed":
        out = [e for e in out if e["direction"] == "borrowed"]
    elif tab == "lent":
        out = [e for e in out if e["direction"] == "lent"]
    elif tab == "pending":
        out = [e for e in out if e["status"] == "pending" or e["awaiting_repayment"] > 0]
    return out


async def party_entry(entry_id: str, uid: str) -> dict:
    e = await db.lending_ledger.find_one({"id": entry_id}, P)
    if not e:
        raise HTTPException(status_code=404, detail="Lending entry not found")
    if uid not in (e["lender_id"], e["borrower_id"]):
        raise HTTPException(status_code=403, detail="Only the two parties can view or act on this entry")
    return e


async def entry_detail(entry_id: str, uid: str) -> dict:
    e = await party_entry(entry_id, uid)
    reps = await db.lending_repayments.find({"loan_id": entry_id}, P).sort("created_at", -1).to_list(500)
    names = await _names({e["lender_id"], e["borrower_id"]} | {h["actor_id"] for h in e.get("history", [])})
    out = serialize(e, uid, names, reps)
    out["repayments"] = [{**r, "can_confirm": r["status"] == "awaiting_confirmation" and r["lender_id"] == uid} for r in reps]
    out["history"] = [{**h, "actor_name": names.get(h["actor_id"])} for h in e.get("history", [])]
    out["disclaimer"] = DISCLAIMER
    return out


async def is_friend(a: str, b: str) -> bool:
    return bool(await db.friendships.find_one({"pair_key": pair_key(a, b), "status": "accepted"}, {"_id": 1}))


def pair_key(a: str, b: str) -> str:
    return ":".join(sorted([a, b]))


async def create_entry(user: dict, kind: str, friend_id: str, amount, text: str, due_date: str | None) -> dict:
    errors = {}
    if not friend_id or not await is_friend(user["id"], friend_id):
        errors["friend_id"] = "Choose one of your friends"
    try:
        credits = parse_credits(amount)
    except HTTPException as exc:
        errors.update(exc.detail["fields"])
        credits = 0
    if kind == "request" and not text.strip():
        errors["reason"] = "Add a short reason"
    if errors:
        raise field_error(422, errors)
    due = parse_due_date(due_date)
    lender, borrower = (friend_id, user["id"]) if kind == "request" else (user["id"], friend_id)
    now = now_iso()
    doc = {"id": new_id("lnd"), "kind": kind, "initiator_id": user["id"], "lender_id": lender, "borrower_id": borrower,
           "credits": credits, "repaid_credits": 0, "status": "pending", "note": text.strip(), "due_date": due,
           "created_at": now, "updated_at": now, "simulated": True,
           "history": [history(user["id"], "requested" if kind == "request" else "offered", amount=credits)]}
    if kind == "offer":
        async with locked(f"lender:{user['id']}"):
            _, b = await balances(user["id"])
            if credits > b["available"]:
                raise field_error(400, {"amount": NOT_ENOUGH})
            await db.lending_ledger.insert_one(doc)
    else:
        await db.lending_ledger.insert_one(doc)
    verb = "requested" if kind == "request" else "offered to lend"
    await notify(friend_id, f"lending.{kind}", f"{user['name']} {verb} {credits:,} credits", {"entry_id": doc["id"]})
    await audit(user["id"], f"lending.{kind}.created", {"entry_id": doc["id"], "credits": credits, "counterparty": friend_id})
    return await entry_detail(doc["id"], user["id"])


async def _transition(entry_id: str, expect: str, new_status: str, actor_id: str, action: str, extra: dict | None = None) -> dict:
    res = await db.lending_ledger.find_one_and_update(
        {"id": entry_id, "status": expect},
        {"$set": {"status": new_status, "updated_at": now_iso(), **(extra or {})}, "$push": {"history": history(actor_id, action)}},
        projection=P, return_document=ReturnDocument.AFTER)
    if not res:
        raise conflict()
    return res


async def respond(user: dict, entry_id: str, action: str) -> dict:
    e = await party_entry(entry_id, user["id"])
    if e["status"] != "pending":
        raise conflict()
    initiator = e.get("initiator_id") == user["id"]
    if action in ("accept", "decline") and initiator:
        raise HTTPException(status_code=403, detail="Only the other party can respond to this entry")
    if action == "cancel" and not initiator:
        raise HTTPException(status_code=403, detail="Only the person who created this entry can cancel it")
    if action == "accept":
        async with locked(f"lender:{e['lender_id']}"):
            _, b = await balances(e["lender_id"])
            if e["credits"] > b["available"]:
                raise bad_request(NOT_ENOUGH)
            await _transition(entry_id, "pending", "active", user["id"], "accepted", {"activated_at": now_iso()})
    else:
        status = {"decline": "declined", "cancel": "cancelled"}[action]
        await _transition(entry_id, "pending", status, user["id"], status)
    past = {"accept": "accepted", "decline": "declined", "cancel": "cancelled"}[action]
    other = e["borrower_id"] if e["lender_id"] == user["id"] else e["lender_id"]
    await notify(other, f"lending.{past}", f"{user['name']} {past} the {e['credits']:,} credit entry", {"entry_id": entry_id})
    await audit(user["id"], f"lending.{past}", {"entry_id": entry_id, "credits": e["credits"]})
    return await entry_detail(entry_id, user["id"])


async def record_repayment(user: dict, entry_id: str, amount) -> dict:
    e = await party_entry(entry_id, user["id"])
    if e["borrower_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the borrower can record a repayment")
    if e["status"] != "active":
        raise bad_request("Repayments can only be recorded on active loans")
    credits = parse_credits(amount)
    async with locked(f"loan:{entry_id}"):
        e = await party_entry(entry_id, user["id"])
        if e["status"] != "active":
            raise bad_request("Repayments can only be recorded on active loans")
        awaiting = sum(r["amount"] for r in await db.lending_repayments.find(
            {"loan_id": entry_id, "status": "awaiting_confirmation"}, P).to_list(500))
        if credits > outstanding(e) - awaiting:
            raise field_error(400, {"amount": "Repayment exceeds outstanding amount"})
        rep = {"id": new_id("rep"), "loan_id": entry_id, "borrower_id": e["borrower_id"], "lender_id": e["lender_id"],
               "amount": credits, "status": "awaiting_confirmation", "created_at": now_iso(), "resolved_at": None}
        await db.lending_repayments.insert_one(rep)
    await db.lending_ledger.update_one({"id": entry_id}, {"$push": {"history": history(user["id"], "repayment_recorded", amount=credits)},
                                                          "$set": {"updated_at": now_iso()}})
    await notify(e["lender_id"], "lending.repayment", f"{user['name']} recorded a {credits:,} credit repayment", {"entry_id": entry_id})
    await audit(user["id"], "lending.repayment.recorded", {"entry_id": entry_id, "repayment_id": rep["id"], "credits": credits})
    return await entry_detail(entry_id, user["id"])


async def resolve_repayment(user: dict, repayment_id: str, action: str) -> dict:
    rep = await db.lending_repayments.find_one({"id": repayment_id}, P)
    if not rep:
        raise HTTPException(status_code=404, detail="Repayment not found")
    if user["id"] not in (rep["lender_id"], rep["borrower_id"]):
        raise HTTPException(status_code=403, detail="Only the two parties can view or act on this entry")
    if rep["lender_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the lender can confirm or dispute a repayment")
    status = "confirmed" if action == "confirm" else "disputed"
    done = await db.lending_repayments.find_one_and_update(
        {"id": repayment_id, "status": "awaiting_confirmation"}, {"$set": {"status": status, "resolved_at": now_iso()}})
    if not done:
        raise conflict()
    amount = rep["amount"]
    if action == "confirm":
        loan = await db.lending_ledger.find_one_and_update(
            {"id": rep["loan_id"], "status": "active", "$expr": {"$lte": [{"$add": ["$repaid_credits", amount]}, "$credits"]}},
            {"$inc": {"repaid_credits": amount}, "$set": {"updated_at": now_iso()},
             "$push": {"history": history(user["id"], "repayment_confirmed", amount=amount)}},
            projection=P, return_document=ReturnDocument.AFTER)
        if not loan:
            await db.lending_repayments.update_one({"id": repayment_id}, {"$set": {"status": "awaiting_confirmation", "resolved_at": None}})
            raise conflict("This loan changed. Refresh and try again.")
        if loan["repaid_credits"] >= loan["credits"]:
            await _transition(loan["id"], "active", "repaid", user["id"], "repaid", {"repaid_at": now_iso()})
    else:
        await db.lending_ledger.update_one({"id": rep["loan_id"]}, {"$push": {"history": history(user["id"], "repayment_disputed", amount=amount)},
                                                                    "$set": {"updated_at": now_iso()}})
    await notify(rep["borrower_id"], f"lending.repayment.{status}", f"{user['name']} {status} your {amount:,} credit repayment",
                 {"entry_id": rep["loan_id"], "repayment_id": repayment_id})
    await audit(user["id"], f"lending.repayment.{status}", {"entry_id": rep["loan_id"], "repayment_id": repayment_id, "credits": amount})
    return await entry_detail(rep["loan_id"], user["id"])
