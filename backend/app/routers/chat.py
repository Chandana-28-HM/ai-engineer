from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ChatRequest, CodeTaskRequest, IntentRequest, IntentResponse
from app.services.chat_service import detect_intent, stream_chat

router = APIRouter(prefix="/api", tags=["chat"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-engineer-backend"}


@router.post("/intent", response_model=IntentResponse)
async def intent(payload: IntentRequest):
    intent_value = detect_intent(payload.message, repo_attached=True)
    return IntentResponse(intent=intent_value, needs_repo=intent_value == "search")


@router.post("/chat")
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    async def generator():
        try:
            async for event in stream_chat(
                db,
                conversation_id=payload.conversation_id,
                project_id=payload.project_id,
                repo_id=payload.repo_id,
                message=payload.message,
            ):
                yield sse(event["event"], event["data"])
        except Exception as exc:  # noqa: BLE001
            yield sse("error", {"message": str(exc)})

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.post("/code/task")
async def code_task(payload: CodeTaskRequest, db: AsyncSession = Depends(get_db)):
    # Reuse the same streaming pipeline; task_type is surfaced in the intent event.
    message = payload.message
    if payload.task_type == "explain" and not any(k in message.lower() for k in ["explain", "what", "how", "why"]):
        message = f"Explain this: {message}"
    elif payload.task_type == "fix" and not any(k in message.lower() for k in ["fix", "bug", "error", "issue"]):
        message = f"Fix this code/error: {message}"
    elif payload.task_type == "generate":
        message = f"Generate code: {message}"

    async def generator():
        try:
            async for event in stream_chat(
                db,
                conversation_id=payload.conversation_id,
                project_id=payload.project_id,
                repo_id=payload.repo_id,
                message=message,
            ):
                yield sse(event["event"], event["data"])
        except Exception as exc:  # noqa: BLE001
            yield sse("error", {"message": str(exc)})

    return StreamingResponse(generator(), media_type="text/event-stream")
