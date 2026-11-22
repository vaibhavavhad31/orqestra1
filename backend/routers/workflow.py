from typing import Any, Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import BaseModel
from core.deps import require_module, require_org
from services import handover, planner

router = APIRouter(tags=["handover & planner"])
ho = require_module("handover")
pl = require_module("planner")
team = require_org("admin", "manager")


class HandoverIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    priority: Optional[str] = None
    completed_work: Optional[str] = None
    pending_work: Optional[str] = None
    context_notes: Optional[str] = None
    assignee_id: Optional[str] = None


class NoteIn(BaseModel):
    note: str = ""


class SessionIn(BaseModel):
    provider_id: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    estimated_credits: Any = None
    purpose: Optional[str] = None
    reminder_min: Optional[int] = None


class SuggestIn(BaseModel):
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    note: str = ""


class ResetIn(BaseModel):
    provider_id: Optional[str] = None
    reset_type: Optional[str] = None
    rolling_hours: Optional[int] = None
    next_reset_at: Optional[str] = None


@router.get("/handovers")
async def list_handovers(box: str = Query("received", pattern="^(received|sent|all)$"), status: Optional[str] = None,
                         user: dict = Depends(ho)):
    return {"tasks": await handover.list_tasks(user, box, status),
            "privacy_note": "Only the context you add here is shared. Your AI chat history is never shared."}


@router.get("/handovers/assignees")
async def handover_assignees(user: dict = Depends(ho)):
    return await handover.assignees(user)


@router.post("/handovers")
async def create_handover(body: HandoverIn, user: dict = Depends(ho)):
    return await handover.create(user, body.model_dump())


@router.get("/handovers/{task_id}")
async def get_handover(task_id: str, user: dict = Depends(ho)):
    return await handover.serialize(user, await handover.get_task(user, task_id), True)


@router.patch("/handovers/{task_id}")
async def edit_handover(task_id: str, body: HandoverIn, user: dict = Depends(ho)):
    return await handover.edit(user, task_id, body.model_dump(exclude_none=True))


@router.post("/handovers/{task_id}/accept")
async def accept_handover(task_id: str, user: dict = Depends(ho)):
    return await handover.transition(user, task_id, "accept")


@router.post("/handovers/{task_id}/reject")
async def reject_handover(task_id: str, body: Optional[NoteIn] = None, user: dict = Depends(ho)):
    return await handover.transition(user, task_id, "reject", body.note if body else "")


@router.post("/handovers/{task_id}/complete")
async def complete_handover(task_id: str, body: Optional[NoteIn] = None, user: dict = Depends(ho)):
    return await handover.transition(user, task_id, "complete", body.note if body else "")


@router.post("/handovers/{task_id}/cancel")
async def cancel_handover(task_id: str, user: dict = Depends(ho)):
    return await handover.transition(user, task_id, "cancel")


@router.post("/handovers/{task_id}/attachments")
async def upload_attachment(task_id: str, file: UploadFile = File(...), user: dict = Depends(ho)):
    return await handover.add_attachment(user, task_id, file)


@router.get("/handovers/{task_id}/attachments/{attachment_id}")
async def download_attachment(task_id: str, attachment_id: str, user: dict = Depends(ho)):
    data, att = await handover.download(user, task_id, attachment_id)
    return Response(content=data, media_type=att["content_type"],
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(att['filename'])}"})


@router.get("/planner/sessions")
async def my_sessions(start: Optional[str] = None, end: Optional[str] = None, user: dict = Depends(pl)):
    return await planner.list_mine(user, start, end)


@router.post("/planner/sessions")
async def create_session(body: SessionIn, user: dict = Depends(pl)):
    return await planner.create(user, body.model_dump())


@router.patch("/planner/sessions/{session_id}")
async def update_session(session_id: str, body: SessionIn, user: dict = Depends(pl)):
    return await planner.update(user, session_id, body.model_dump(exclude_unset=True))


@router.post("/planner/sessions/{session_id}/cancel")
async def cancel_session(session_id: str, user: dict = Depends(pl)):
    return await planner.set_status(user, session_id, "cancelled")


@router.post("/planner/sessions/{session_id}/complete")
async def complete_session(session_id: str, user: dict = Depends(pl)):
    return await planner.set_status(user, session_id, "completed")


@router.post("/planner/sessions/{session_id}/suggestion/accept")
async def accept_suggestion(session_id: str, user: dict = Depends(pl)):
    return await planner.respond_suggestion(user, session_id, True)


@router.post("/planner/sessions/{session_id}/suggestion/dismiss")
async def dismiss_suggestion(session_id: str, user: dict = Depends(pl)):
    return await planner.respond_suggestion(user, session_id, False)


@router.get("/planner/team")
async def team_sessions(start: Optional[str] = None, end: Optional[str] = None, member_id: Optional[str] = None,
                        user: dict = Depends(team)):
    return await planner.list_team(user, start, end, member_id)


@router.post("/planner/team/sessions/{session_id}/suggest")
async def suggest_time(session_id: str, body: SuggestIn, user: dict = Depends(team)):
    return await planner.suggest(user, session_id, body.model_dump())


@router.get("/planner/resets")
async def resets(user: dict = Depends(pl)):
    return await planner.list_resets(user)


@router.post("/planner/resets")
async def save_reset(body: ResetIn, user: dict = Depends(pl)):
    return await planner.save_reset(user, body.model_dump())


@router.delete("/planner/resets/{reset_id}")
async def delete_reset(reset_id: str, user: dict = Depends(pl)):
    return await planner.delete_reset(user, reset_id)
