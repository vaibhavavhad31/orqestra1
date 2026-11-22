from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from core.deps import require_module, require_org
from services import allocation
from services.usage import check_days

router = APIRouter(prefix="/allocation", tags=["allocation"])
any_org = require_module("allocation")
approver = require_org("admin", "manager")
admin_only = require_org("admin")


class CreditsIn(BaseModel):
    credits: Any = None


class ReallocateIn(BaseModel):
    from_user_id: str = ""
    to_user_id: str = ""
    credits: Any = None


class RequestIn(BaseModel):
    amount: Any = None
    reason: str = ""
    urgency: str = "normal"


class RejectIn(BaseModel):
    note: str = ""


@router.get("")
async def get_allocation(days: int = Query(30), user: dict = Depends(any_org)):
    check_days(days)
    return await allocation.overview(user, days)


@router.put("/org")
async def update_org_budget(body: CreditsIn, user: dict = Depends(admin_only)):
    await allocation.set_org_budget(user, body.credits)
    return {"ok": True}


@router.put("/departments/{dept_id}")
async def update_department(dept_id: str, body: CreditsIn, user: dict = Depends(admin_only)):
    await allocation.set_dept_budget(user, dept_id, body.credits)
    return {"ok": True}


@router.put("/members/{member_id}")
async def update_member(member_id: str, body: CreditsIn, user: dict = Depends(approver)):
    await allocation.set_member_allocation(user, member_id, body.credits)
    return {"ok": True}


@router.post("/reallocate")
async def reallocate(body: ReallocateIn, user: dict = Depends(approver)):
    await allocation.reallocate(user, body.from_user_id, body.to_user_id, body.credits)
    return {"ok": True}


@router.get("/requests")
async def list_requests(user: dict = Depends(any_org)):
    data = await allocation.overview(user, 30)
    return data["requests"]


@router.post("/requests")
async def create_request(body: RequestIn, user: dict = Depends(any_org)):
    return await allocation.create_request(user, body.amount, body.reason, body.urgency)


@router.post("/requests/{request_id}/approve")
async def approve(request_id: str, body: CreditsIn, user: dict = Depends(approver)):
    return await allocation.approve_request(user, request_id, body.credits)


@router.post("/requests/{request_id}/reject")
async def reject(request_id: str, body: RejectIn, user: dict = Depends(approver)):
    return await allocation.reject_request(user, request_id, body.note)


@router.post("/requests/{request_id}/cancel")
async def cancel(request_id: str, user: dict = Depends(any_org)):
    return await allocation.cancel_request(user, request_id)
