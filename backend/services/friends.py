from fastapi import HTTPException
from core.db import db, new_id, now_iso
from services.actions import conflict, notify
from services.lending import pair_key
from services.users import audit

NO_INDIVIDUAL = "No individual user found with that email"
P = {"_id": 0}


async def list_friends(uid: str) -> dict:
    docs = await db.friendships.find({"$or": [{"requester_id": uid}, {"addressee_id": uid}],
                                      "status": {"$in": ["pending", "accepted"]}}, P).sort("created_at", -1).to_list(1000)
    other_ids = {d["addressee_id"] if d["requester_id"] == uid else d["requester_id"] for d in docs}
    users = {u["id"]: u async for u in db.users.find({"id": {"$in": list(other_ids)}}, {"_id": 0, "id": 1, "name": 1, "email": 1})}
    out = {"friends": [], "incoming": [], "outgoing": []}
    for d in docs:
        other = d["addressee_id"] if d["requester_id"] == uid else d["requester_id"]
        item = {"id": d["id"], "user": users.get(other), "status": d["status"], "created_at": d["created_at"],
                "responded_at": d.get("responded_at")}
        if d["status"] == "accepted":
            out["friends"].append(item)
        elif d["addressee_id"] == uid:
            out["incoming"].append(item)
        else:
            out["outgoing"].append(item)
    return out


async def send_request(user: dict, email: str) -> dict:
    email = email.strip().lower()
    target = await db.users.find_one({"email": email, "mode": "individual"}, {"_id": 0, "id": 1, "name": 1})
    if not target:
        raise HTTPException(status_code=404, detail={"message": NO_INDIVIDUAL, "fields": {"email": NO_INDIVIDUAL}})
    if target["id"] == user["id"]:
        raise HTTPException(status_code=400, detail={"message": "You can't add yourself", "fields": {"email": "You can't add yourself"}})
    key = pair_key(user["id"], target["id"])
    existing = await db.friendships.find_one({"pair_key": key}, P)
    if existing and existing["status"] == "accepted":
        raise HTTPException(status_code=409, detail={"message": "You're already friends", "fields": {"email": "You're already friends"}})
    if existing and existing["status"] == "pending":
        msg = "A friend request is already pending"
        raise HTTPException(status_code=409, detail={"message": msg, "fields": {"email": msg}})
    now = now_iso()
    if existing:
        await db.friendships.update_one({"pair_key": key}, {"$set": {"requester_id": user["id"], "addressee_id": target["id"],
                                                                      "status": "pending", "created_at": now, "responded_at": None}})
        fid = existing["id"]
    else:
        fid = new_id("frn")
        await db.friendships.insert_one({"id": fid, "pair_key": key, "requester_id": user["id"], "addressee_id": target["id"],
                                         "status": "pending", "created_at": now, "responded_at": None})
    await notify(target["id"], "friend.request", f"{user['name']} wants to connect", {"friendship_id": fid})
    await audit(user["id"], "friend.requested", {"friendship_id": fid, "target_id": target["id"]})
    return await list_friends(user["id"])


async def respond_request(user: dict, friendship_id: str, accept: bool) -> dict:
    doc = await db.friendships.find_one({"id": friendship_id}, P)
    if not doc or user["id"] not in (doc["requester_id"], doc["addressee_id"]):
        raise HTTPException(status_code=404, detail="Friend request not found")
    if doc["addressee_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the invited person can respond")
    status = "accepted" if accept else "declined"
    done = await db.friendships.find_one_and_update({"id": friendship_id, "status": "pending"},
                                                    {"$set": {"status": status, "responded_at": now_iso()}})
    if not done:
        raise conflict()
    await notify(doc["requester_id"], f"friend.{status}", f"{user['name']} {status} your friend request", {"friendship_id": friendship_id})
    await audit(user["id"], f"friend.{status}", {"friendship_id": friendship_id})
    return await list_friends(user["id"])
