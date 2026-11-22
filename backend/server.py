import asyncio
import logging
from pathlib import Path
from core.config import CORS_ORIGINS, FRONTEND_BUILD_DIR, ENABLE_EMERGENT_GOOGLE_AUTH, LLM_API_KEY
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from core.db import client
from core.indexes import ensure_indexes
from services.seed import run_seed
from routers import auth, demo, dashboard, org, lending, allocation, workflow, workspace, team, tasks
from services.planner import reminder_loop
from services.storage import init_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="Orqestra API", version="4.0.0",
              openapi_url="/api/openapi.json", docs_url="/api/docs", redoc_url=None)

for module in (auth, demo, dashboard, org, lending, allocation, workflow, workspace, team, tasks):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/api/config", tags=["system"])
async def public_config():
    """Non-secret feature flags for the frontend."""
    return {"google_auth": ENABLE_EMERGENT_GOOGLE_AUTH, "llm_decomposition": bool(LLM_API_KEY)}


if CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    await run_seed()
    try:
        await asyncio.to_thread(init_storage)
    except Exception as exc:
        logging.getLogger("storage").error("Storage init failed: %s", exc)
    app.state.reminders = asyncio.create_task(reminder_loop())


@app.on_event("shutdown")
async def shutdown():
    client.close()


# Serve the built React app from the same origin (single free web service). API routes above take priority.
if FRONTEND_BUILD_DIR and Path(FRONTEND_BUILD_DIR, "index.html").exists():
    _build = Path(FRONTEND_BUILD_DIR).resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        target = (_build / full_path).resolve()
        if full_path and target.is_file() and _build in target.parents:
            return FileResponse(target)
        return FileResponse(_build / "index.html", headers={"Cache-Control": "no-cache"})
