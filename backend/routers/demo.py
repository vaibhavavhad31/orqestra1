from fastapi import APIRouter, Depends, HTTPException, Response
from core.db import db
from core.deps import get_current_user, forbidden, PUBLIC_USER
from core.permissions import ROLE_LABELS
from core.sessions import start_session
from models.schemas import DemoLoginIn, DemoSwitchIn, DemoAccountOut, AuthOut
from services.users import serialize_user, audit

router = APIRouter(prefix="/demo", tags=["demo"])

DESCRIPTIONS = {
    "admin": "Org-wide budget, departments and spend",
    "manager": "Engineering team usage and allocations",
    "employee": "Personal allocation and own usage",
    "individual": "Personal credits and lending with friends",
}
FRIENDS = {
    "tomas": "Maya's friend · borrower on an overdue loan",
    "hana": "Maya's friend · lender awaiting a repayment confirmation",
    "kwame": "Maya's friend · low available credits",
}


async def _demo_users(include_friends: bool = False) -> list[dict]:
    order = list(DESCRIPTIONS) + (list(FRIENDS) if include_friends else [])
    users = await db.users.find({"is_demo": True, "demo_key": {"$in": order}}, PUBLIC_USER).to_list(20)
    return sorted(users, key=lambda u: order.index(u["demo_key"]))


@router.get("/accounts", response_model=list[DemoAccountOut])
async def demo_accounts(include_friends: bool = False):
    orgs = {o["id"]: o["name"] async for o in db.organizations.find({"is_demo": True}, {"_id": 0, "id": 1, "name": 1})}
    return [DemoAccountOut(key=u["demo_key"], user_id=u["id"], name=u["name"], title=u.get("title"), email=u["email"],
                           role=u["role"], role_label=ROLE_LABELS[u["role"]],
                           workspace=orgs.get(u.get("org_id"), "Personal workspace"),
                           description=DESCRIPTIONS.get(u["demo_key"]) or FRIENDS[u["demo_key"]],
                           group="primary" if u["demo_key"] in DESCRIPTIONS else "friends")
            for u in await _demo_users(include_friends)]


@router.post("/login", response_model=AuthOut)
async def demo_login(body: DemoLoginIn, response: Response):
    user = await db.users.find_one({"is_demo": True, "demo_key": body.key}, PUBLIC_USER)
    if not user:
        raise HTTPException(status_code=404, detail="Demo account not found")
    await audit(user["id"], "auth.login", {"method": "demo"})
    return AuthOut(user=await serialize_user(user), access_token=await start_session(response, user["id"]))


@router.post("/switch", response_model=AuthOut)
async def demo_switch(body: DemoSwitchIn, response: Response, current: dict = Depends(get_current_user)):
    if not current.get("is_demo"):
        raise forbidden("View as role is only available for demo accounts")
    target = await db.users.find_one({"id": body.target_user_id}, PUBLIC_USER)
    if not target or not target.get("is_demo"):
        raise forbidden("You can only switch to another demo account")
    await audit(current["id"], "demo.switch", {"target_user_id": target["id"]})
    return AuthOut(user=await serialize_user(target), access_token=await start_session(response, target["id"]))
