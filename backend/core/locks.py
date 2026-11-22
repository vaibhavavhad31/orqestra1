import asyncio
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from core.db import db, now_utc

LOCK_TTL = timedelta(seconds=30)


@asynccontextmanager
async def locked(*keys: str, timeout: float = 5.0):
    """Serialise invariant checks across documents (per lender / department / org). Keys are taken in sorted order."""
    taken: list[str] = []
    try:
        for key in sorted(set(keys)):
            deadline = time.monotonic() + timeout
            while True:
                try:
                    await db.locks.insert_one({"_id": key, "expires_at": now_utc() + LOCK_TTL})
                    taken.append(key)
                    break
                except DuplicateKeyError:
                    await db.locks.delete_one({"_id": key, "expires_at": {"$lt": now_utc()}})
                    if time.monotonic() > deadline:
                        raise HTTPException(status_code=409, detail="Another action is in progress. Please try again.")
                    await asyncio.sleep(0.03)
        yield
    finally:
        if taken:
            await db.locks.delete_many({"_id": {"$in": taken}})
