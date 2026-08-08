from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import AgentRun, AgentStep, Repository
from app.services.agent import graph as agent_graph
from app.utils.fs import list_files, relative

STEP_ORDER = ["planner", "coder", "reviewer", "debugger", "documenter"]
STEP_LABELS = {
    "planner": "Planner",
    "coder": "Coder",
    "reviewer": "Reviewer",
    "debugger": "Debugger",
    "documenter": "Documenter",
}


async def create_run(db: AsyncSession, payload: Any) -> AgentRun:
    run = AgentRun(
        project_id=payload.project_id,
        conversation_id=payload.conversation_id,
        repo_id=payload.repo_id,
        kind=payload.kind,
        goal=payload.goal,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def _step_index(agent: str) -> int:
    return STEP_ORDER.index(agent) if agent in STEP_ORDER else 99


async def _persist_step(run_id: int, data: dict) -> None:
    """Persist an agent step using its own session (safe for concurrent tasks)."""
    db = AsyncSessionLocal()
    try:
        agent = data.get("agent", "agent")
        step = AgentStep(
            run_id=run_id,
            step_index=await _step_index(agent),
            agent=agent,
            title=STEP_LABELS.get(agent, agent),
            status=data.get("status", "running"),
        )
        if data.get("plan"):
            step.output_text = json.dumps(data["plan"], ensure_ascii=False)[:4000]
        if data.get("output"):
            step.output_text = data["output"]
        if data.get("comments"):
            step.output_text = json.dumps(data["comments"], ensure_ascii=False)[:4000]
        if data.get("files"):
            step.files_changed = json.dumps(data["files"], ensure_ascii=False)
        db.add(step)
        await db.commit()
    finally:
        await db.close()


async def _update_run_status(
    run_id: int, status: str, summary: str | None = None, error: str | None = None
) -> None:
    """Update run status in its own session (the run object is detached here)."""
    db = AsyncSessionLocal()
    try:
        run = await db.get(AgentRun, run_id)
        if run:
            run.status = status
            run.summary = summary
            run.error = error
            run.completed_at = datetime.now()
            await db.commit()
    finally:
        await db.close()


async def execute_run(run: AgentRun, publish: Any) -> None:
    """Execute an agent run, persisting steps and emitting events."""
    db = AsyncSessionLocal()
    pending_tasks: list[asyncio.Task] = []
    try:
        workspace = _project_workspace(run)
        if run.repo_id:
            repo = await db.get(Repository, run.repo_id)
            if repo:
                workspace = Path(repo.local_path).resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        def handler(event: dict) -> None:
            publish(event)
            if event.get("event") == "step":
                pending_tasks.append(asyncio.create_task(_persist_step(run.id, event["data"])))

        publish({"event": "run_start", "data": {"run_id": run.id, "kind": run.kind, "goal": run.goal}})

        if run.kind == "single":
            await agent_graph.run_single_agent(workspace, run.goal, publish=handler)
            summary = "Single-agent run completed."
        else:
            result = await agent_graph.run_multi_agent(workspace, run.goal, publish=handler)
            summary = result.get("final_docs") or "Multi-agent run completed."

        if pending_tasks:
            await asyncio.gather(*pending_tasks)

        await _update_run_status(run.id, "done", summary=summary)
        publish({"event": "run_done", "data": {"run_id": run.id, "summary": summary}})
    except Exception as exc:  # noqa: BLE001
        await _update_run_status(run.id, "failed", error=str(exc))
        publish({"event": "run_error", "data": {"message": str(exc)}})
    finally:
        for task in pending_tasks:
            if not task.done():
                task.cancel()
        await db.close()


def _project_workspace(run: AgentRun) -> Path:
    from app.config import settings

    return settings.workspaces_dir / str(run.project_id) / "scratch"


async def list_runs(db: AsyncSession, project_id: int, limit: int = 50) -> list[AgentRun]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())


async def get_run_detail(db: AsyncSession, run_id: int) -> AgentRun | None:
    return await db.get(AgentRun, run_id)


def workspace_files(workspace: Path) -> list[str]:
    return [relative(workspace, f) for f in list_files(workspace)]
