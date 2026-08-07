from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AgentRun, Repository
from app.schemas import AgentRunDetail, AgentRunRead, AgentRunRequest
from app.services.agent import run_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/run", status_code=202)
async def run_agent(payload: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    run = await run_service.create_run(db, payload)

    async def generator():
        queue: asyncio.Queue = asyncio.Queue()

        def publish(event: dict) -> None:
            queue.put_nowait(event)

        task = asyncio.create_task(run_service.execute_run(run, publish))
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield sse("error", {"message": "Agent run timed out"})
                    break
                yield sse(event.get("event", "message"), event.get("data", {}))
                if event.get("event") in ("run_done", "run_error"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/runs", response_model=list[AgentRunRead])
async def list_runs(project_id: int, db: AsyncSession = Depends(get_db)):
    return await run_service.list_runs(db, project_id)


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def run_detail(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await run_service.get_run_detail(db, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/runs/{run_id}/steps", response_model=list)
async def run_steps(run_id: int, db: AsyncSession = Depends(get_db)):
    from app.models import AgentStep

    run = await db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    result = await db.execute(
        select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.id)
    )
    steps = list(result.scalars())
    return [
        {
            "id": s.id,
            "agent": s.agent,
            "title": s.title,
            "status": s.status,
            "output": s.output_text,
            "files_changed": json.loads(s.files_changed) if s.files_changed else [],
        }
        for s in steps
    ]
