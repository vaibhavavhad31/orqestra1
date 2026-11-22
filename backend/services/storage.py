"""Handover attachment storage in MongoDB GridFS (replaces Emergent Object Storage).

Same interface as before: put_object(path, data, content_type) -> {"path": ...}; get_object(path) -> bytes.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from core.db import db

APP_NAME = "orqestra"
BUCKET = "attachment_files"
log = logging.getLogger("storage")
_bucket: AsyncIOMotorGridFSBucket | None = None


def _fs() -> AsyncIOMotorGridFSBucket:
    global _bucket
    if _bucket is None:
        _bucket = AsyncIOMotorGridFSBucket(db, bucket_name=BUCKET)
    return _bucket


def init_storage(force: bool = False) -> str:
    """Kept for compatibility with server startup; GridFS needs no remote initialisation."""
    return BUCKET


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    await _fs().upload_from_stream(path, data, metadata={"content_type": content_type})
    return {"path": path, "size": len(data)}


async def get_object(path: str) -> bytes:
    stream = await _fs().open_download_stream_by_name(path)
    return await stream.read()
