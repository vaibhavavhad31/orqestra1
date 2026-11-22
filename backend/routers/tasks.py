from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from core.deps import require_module
from services import tasks
from services.decompose import decompose

router = APIRouter(tags=["tasks"])
tk = require_module("tasks")


class DecomposeIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "medium"


class GoalIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    deadline: Optional[str] = None
    method: Optional[str] = None
    subtasks: list[dict[str, Any]] = []


class GoalPatch(BaseModel):
    status: Optional[str] = None
    summary: Optional[str] = None


class SlotIn(BaseModel):
    tz_offset: int = 0


class ScheduleIn(BaseModel):
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    provider_id: Optional[str] = None


@router.post("/tasks/decompose")
async def decompose_goal(body: DecomposeIn, user: dict = Depends(tk)):
    return await decompose(body.title or "", body.description or "", body.priority or "medium")


@router.get("/tasks")
async def list_goals(scope: str = Query("mine"), user: dict = Depends(tk)):
    return {"goals": await tasks.list_goals(user, "team" if scope == "team" else "mine")}


@router.post("/tasks")
async def create_goal(body: GoalIn, user: dict = Depends(tk)):
    return await tasks.create_goal(user, body.model_dump())


@router.get("/tasks/people")
async def people(user: dict = Depends(tk)):
    return {"people": await tasks.candidate_pool(user)}


@router.get("/tasks/{goal_id}")
async def get_goal(goal_id: str, user: dict = Depends(tk)):
    return await tasks.get_goal(user, goal_id)


@router.patch("/tasks/{goal_id}")
async def update_goal(goal_id: str, body: GoalPatch, user: dict = Depends(tk)):
    return await tasks.update_goal(user, goal_id, body.model_dump(exclude_none=True))


@router.delete("/tasks/{goal_id}")
async def delete_goal(goal_id: str, user: dict = Depends(tk)):
    return await tasks.delete_goal(user, goal_id)


@router.patch("/subtasks/{task_id}")
async def update_subtask(task_id: str, body: dict[str, Any], user: dict = Depends(tk)):
    return await tasks.update_subtask(user, task_id, body)


@router.get("/subtasks/{task_id}/candidates")
async def candidates(task_id: str, user: dict = Depends(tk)):
    return await tasks.candidates(user, task_id)


@router.post("/subtasks/{task_id}/slot")
async def suggest_slot(task_id: str, body: SlotIn, user: dict = Depends(tk)):
    return await tasks.suggest_slot(user, task_id, body.tz_offset)


@router.post("/subtasks/{task_id}/schedule")
async def schedule(task_id: str, body: ScheduleIn, user: dict = Depends(tk)):
    return await tasks.schedule(user, task_id, body.model_dump())
