from __future__ import annotations

import json
from typing import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, Repository
from app.services.llm import prompts
from app.services.llm.factory import get_chat_model
from app.services.repo_service import get_structure, search_repo

SYSTEM_PROMPTS = {
    "chat": prompts.GENERAL,
    "generate": prompts.GENERATE,
    "explain": prompts.EXPLAIN,
    "fix": prompts.FIX,
}

SEARCH_KEYWORDS = [
    "find", "search", "where is", "locate", "look for", "grep", "which file",
    "what file", "references", "usage of", "definition of", "how is this used",
]

GENERATE_KEYWORDS = ["generate", "create a", "write a", "write code", "implement", "build a", "make a", "add a function", "new file"]
EXPLAIN_KEYWORDS = ["explain", "what does this", "how does this", "walk me through", "understand this", "what is this code"]
FIX_KEYWORDS = ["fix", "bug", "error", "not working", "broken", "crash", "debug", "issue", "exception", "fails", "typo"]


def detect_intent(message: str, repo_attached: bool) -> str:
    lowered = message.lower().strip()
    if repo_attached and any(k in lowered for k in SEARCH_KEYWORDS):
        return "search"
    if any(k in lowered for k in EXPLAIN_KEYWORDS):
        return "explain"
    if any(k in lowered for k in FIX_KEYWORDS):
        return "fix"
    if any(k in lowered for k in GENERATE_KEYWORDS):
        return "generate"
    return "chat"


async def build_history(db: AsyncSession, conversation_id: int | None, limit: int = 12) -> list[dict]:
    if not conversation_id:
        return []
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def save_message(
    db: AsyncSession, conversation_id: int, role: str, content: str, sources: str | None = None
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def ensure_conversation(db: AsyncSession, conversation_id: int | None, project_id: int | None) -> Conversation:
    if conversation_id:
        conversation = await db.get(Conversation, conversation_id)
        if conversation:
            return conversation
    conversation = Conversation(project_id=project_id, title="New chat")
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def _repo_payload(db: AsyncSession, repo_id: int | None) -> tuple[str | None, list[str]]:
    """Return (structure_summary, file_list) if a repo is attached."""
    if not repo_id:
        return None, []
    repo = await db.get(Repository, repo_id)
    if repo is None or repo.status != "indexed":
        return None, []
    try:
        structure = await get_structure(db, repo)
        return structure["summary"], [f["path"] for f in _flatten(structure["file_tree"])]
    except Exception:  # noqa: BLE001
        return None, []


def _flatten(tree: list[dict]) -> list[dict]:
    out: list[dict] = []
    for node in tree:
        if node["type"] == "file":
            out.append(node)
        else:
            out.extend(_flatten(node.get("children", [])))
    return out


async def stream_chat(
    db: AsyncSession,
    conversation_id: int | None,
    project_id: int | None,
    repo_id: int | None,
    message: str,
) -> AsyncIterator[dict]:
    """Stream an assistant response as a series of event dicts."""
    conversation = await ensure_conversation(db, conversation_id, project_id)
    user_msg = await save_message(db, conversation.id, "user", message)

    if conversation.title == "New chat":
        conversation.title = (message[:60] + ("…" if len(message) > 60 else ""))
        await db.commit()

    repo = await db.get(Repository, repo_id) if repo_id else None
    repo_attached = repo is not None and repo.status == "indexed"
    intent = detect_intent(message, repo_attached)
    yield {"event": "intent", "data": {"intent": intent, "conversation_id": conversation.id}}

    history = await build_history(db, conversation.id, limit=12)
    # Drop the current user message from history; we append it explicitly.
    if history and history[-1]["content"] == message and history[-1]["role"] == "user":
        history = history[:-1]

    sources_json: str | None = None
    system = SYSTEM_PROMPTS.get(intent, prompts.GENERAL)
    extra_context = prompts.repo_context()
    llm_messages = history + [{"role": "user", "content": message}]

    # Pre-built RAG answer path (search intent with repo attached).
    prebuilt_answer: str | None = None

    if intent == "search" and repo:
        search = await search_repo(db, repo, message, limit=5, answer=True)
        sources_json = json.dumps(
            [{"file_path": s.file_path, "line": s.line, "score": s.score} for s in search.results],
            ensure_ascii=False,
        )
        yield {"event": "sources", "data": {"sources": [s.model_dump() for s in search.results]}}
        if search.answered:
            prebuilt_answer = search.answered
        else:
            system = prompts.CODE_SEARCH
    else:
        structure_summary_text, file_list = await _repo_payload(db, repo_id)
        if structure_summary_text:
            extra_context = prompts.repo_context(structure=structure_summary_text, tree=file_list)

    if prebuilt_answer:
        assistant_content = prebuilt_answer
        yield {"event": "done", "data": {"message_id": 0}}
    else:
        if extra_context:
            system = f"{system}\n\n{extra_context}"
        assistant_content = ""
        model = get_chat_model()
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        langchain_history: list = []
        if system:
            langchain_history.append(SystemMessage(content=system))
        for h in llm_messages:
            langchain_history.append(
                AIMessage(content=h["content"]) if h["role"] == "assistant" else HumanMessage(content=h["content"])
            )

        try:
            async for chunk in model.astream(langchain_history):
                piece = getattr(chunk, "content", "") or ""
                if piece:
                    assistant_content += piece
                    yield {"event": "token", "data": {"text": piece}}
        except Exception as exc:  # noqa: BLE001
            assistant_content = f"\n\n> ⚠️ LLM error: {exc}"
            yield {"event": "error", "data": {"message": str(exc)}}

    saved = await save_message(db, conversation.id, "assistant", assistant_content, sources=sources_json)
    yield {"event": "done", "data": {"message_id": saved.id}}
