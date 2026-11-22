import logging
from pymongo import ASCENDING as A, DESCENDING as D, IndexModel
from core.db import db


def _id():
    return IndexModel([("id", A)], name="id", unique=True)


INDEXES: dict[str, list[IndexModel]] = {
    "users": [_id(), IndexModel([("email", A)], name="email", unique=True),
              IndexModel([("org_id", A), ("department_id", A)], name="org_dept")],
    "organizations": [_id()],
    "departments": [_id(), IndexModel([("org_id", A)], name="org")],
    "providers": [_id(), IndexModel([("sort_order", A)], name="sort")],
    "usage_records": [_id(), IndexModel([("org_id", A), ("date", A)], name="org_date"),
                      IndexModel([("department_id", A), ("date", A)], name="dept_date"),
                      IndexModel([("user_id", A), ("date", A)], name="user_date")],
    "allocations": [_id(), IndexModel([("scope_type", A), ("scope_id", A)], name="scope")],
    "lending_ledger": [_id(), IndexModel([("lender_id", A)], name="lender"),
                       IndexModel([("borrower_id", A)], name="borrower")],
    "lending_repayments": [_id(), IndexModel([("loan_id", A)], name="loan"),
                           IndexModel([("lender_id", A), ("status", A)], name="lender_status")],
    "friendships": [_id(), IndexModel([("pair_key", A)], name="pair", unique=True),
                    IndexModel([("requester_id", A)], name="requester"), IndexModel([("addressee_id", A)], name="addressee")],
    "resource_requests": [_id(), IndexModel([("org_id", A), ("status", A)], name="org_status"),
                          IndexModel([("requester_id", A)], name="requester")],
    "handovers": [_id(), IndexModel([("from_user_id", A)], name="from"), IndexModel([("to_user_id", A)], name="to"),
                  IndexModel([("creator_id", A)], name="creator"), IndexModel([("assignee_id", A)], name="assignee"),
                  IndexModel([("org_id", A)], name="org")],
    "attachments": [_id(), IndexModel([("task_id", A)], name="task")],
    "provider_resets": [_id(), IndexModel([("user_id", A), ("provider_id", A)], name="user_provider", unique=True)],
    "sessions": [_id(), IndexModel([("user_id", A), ("start_at", A)], name="user_start"),
                 IndexModel([("status", A), ("reminder_sent", A), ("remind_at", A)], name="reminders"),
                 IndexModel([("org_id", A), ("department_id", A)], name="org_dept")],
    "notifications": [_id(), IndexModel([("user_id", A), ("created_at", D)], name="user_created")],
    "audit_log": [IndexModel([("actor_id", A), ("created_at", D)], name="actor_created")],
    "login_attempts": [IndexModel([("identifier", A)], name="identifier", unique=True)],
    "pending_google_signups": [IndexModel([("token", A)], name="token", unique=True),
                               IndexModel([("expires_at", A)], name="ttl", expireAfterSeconds=0)],
    "tasks": [_id(), IndexModel([("root_id", A)], name="root"), IndexModel([("owner_id", A)], name="owner"),
              IndexModel([("assignee_id", A)], name="assignee"), IndexModel([("org_id", A)], name="org")],
    "seed_meta": [_id()],
    "locks": [IndexModel([("expires_at", A)], name="ttl", expireAfterSeconds=0)],
    "auth_sessions": [IndexModel([("sid", A)], name="sid", unique=True), IndexModel([("user_id", A)], name="user"),
                      IndexModel([("expires_at", A)], name="ttl", expireAfterSeconds=0)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logging.getLogger(__name__).error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
