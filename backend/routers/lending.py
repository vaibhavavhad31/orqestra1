from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from core.deps import require_module
from services import friends, lending

router = APIRouter(tags=["lending"])
indiv = require_module("lending")


class FriendRequestIn(BaseModel):
    email: str = ""


class LendingCreateIn(BaseModel):
    friend_id: str = ""
    amount: Any = None
    reason: str = ""
    due_date: Optional[str] = None


class AmountIn(BaseModel):
    amount: Any = None


@router.get("/friends")
async def get_friends(user: dict = Depends(indiv)):
    return await friends.list_friends(user["id"])


@router.post("/friends/requests")
async def add_friend(body: FriendRequestIn, user: dict = Depends(indiv)):
    return await friends.send_request(user, body.email)


@router.post("/friends/requests/{friendship_id}/accept")
async def accept_friend(friendship_id: str, user: dict = Depends(indiv)):
    return await friends.respond_request(user, friendship_id, True)


@router.post("/friends/requests/{friendship_id}/decline")
async def decline_friend(friendship_id: str, user: dict = Depends(indiv)):
    return await friends.respond_request(user, friendship_id, False)


@router.get("/lending/summary")
async def lending_summary(user: dict = Depends(indiv)):
    return await lending.summary(user["id"])


@router.get("/lending/entries")
async def list_entries(tab: str = Query("all", pattern="^(all|borrowed|lent|pending)$"), user: dict = Depends(indiv)):
    return {"entries": await lending.list_entries(user["id"], tab), "disclaimer": lending.DISCLAIMER, "simulated": True}


@router.get("/lending/ledger")
async def ledger(user: dict = Depends(indiv)):
    return {"entries": await lending.list_entries(user["id"]), "disclaimer": lending.DISCLAIMER, "simulated": True}


@router.get("/lending/entries/{entry_id}")
async def entry(entry_id: str, user: dict = Depends(indiv)):
    return await lending.entry_detail(entry_id, user["id"])


@router.post("/lending/requests")
async def request_credits(body: LendingCreateIn, user: dict = Depends(indiv)):
    return await lending.create_entry(user, "request", body.friend_id, body.amount, body.reason, body.due_date)


@router.post("/lending/offers")
async def offer_credits(body: LendingCreateIn, user: dict = Depends(indiv)):
    return await lending.create_entry(user, "offer", body.friend_id, body.amount, body.reason, body.due_date)


@router.post("/lending/entries/{entry_id}/accept")
async def accept(entry_id: str, user: dict = Depends(indiv)):
    return await lending.respond(user, entry_id, "accept")


@router.post("/lending/entries/{entry_id}/decline")
async def decline(entry_id: str, user: dict = Depends(indiv)):
    return await lending.respond(user, entry_id, "decline")


@router.post("/lending/entries/{entry_id}/cancel")
async def cancel(entry_id: str, user: dict = Depends(indiv)):
    return await lending.respond(user, entry_id, "cancel")


@router.post("/lending/entries/{entry_id}/repayments")
async def repay(entry_id: str, body: AmountIn, user: dict = Depends(indiv)):
    return await lending.record_repayment(user, entry_id, body.amount)


@router.post("/lending/repayments/{repayment_id}/confirm")
async def confirm(repayment_id: str, user: dict = Depends(indiv)):
    return await lending.resolve_repayment(user, repayment_id, "confirm")


@router.post("/lending/repayments/{repayment_id}/dispute")
async def dispute(repayment_id: str, user: dict = Depends(indiv)):
    return await lending.resolve_repayment(user, repayment_id, "dispute")
