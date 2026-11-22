from fastapi import APIRouter, Depends
from core.db import db
from core.deps import require_org
from services.usage import allocation_map

router = APIRouter(tags=["organisation"])


@router.get("/org")
async def get_org(user: dict = Depends(require_org())):
    org = await db.organizations.find_one({"id": user["org_id"]}, {"_id": 0})
    budget = (await allocation_map("org", [org["id"]])).get(org["id"], 0)
    return {"id": org["id"], "name": org["name"], "monthly_budget": budget,
            "employees": await db.users.count_documents({"org_id": org["id"], "status": {"$ne": "deactivated"}}),
            "departments": await db.departments.count_documents({"org_id": org["id"]})}


@router.get("/org/departments")
async def departments(user: dict = Depends(require_org("admin", "manager"))):
    query = {"org_id": user["org_id"]}
    if user["role"] == "manager":
        query["id"] = user["department_id"]
    depts = await db.departments.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    allocs = await allocation_map("department", [d["id"] for d in depts])
    out = []
    for d in depts:
        out.append({"id": d["id"], "name": d["name"], "manager_id": d.get("manager_id"),
                    "monthly_allocation": allocs.get(d["id"], 0),
                    "members": await db.users.count_documents({"department_id": d["id"], "status": {"$ne": "deactivated"}})})
    return out
