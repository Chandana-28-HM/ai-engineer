from __future__ import annotations

import re
from typing import Any, AsyncIterator, Iterator, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings

OFFLINE_NOTICE = (
    "> ⚙️ **No LLM API key configured — running in offline mode.**\n"
    "> Add a `GEMINI_API_KEY` to `backend/.env` (or set `LLM_PROVIDER` to "
    "`ollama`/`deepseek`/`openrouter`) and restart the backend to get real model answers.\n\n"
)


class OfflineChatModel(BaseChatModel):
    """Deterministic offline fallback so chat works with zero API keys."""

    model_name: str = "offline-mock"

    @property
    def _llm_type(self) -> str:
        return "offline-mock"

    def _reply(self, messages: list[BaseMessage]) -> str:
        last_user = ""
        for m in reversed(messages):
            if m.type == "human":
                last_user = str(getattr(m, "content", "")).strip()[:300]
                break
        body = f"You said: \"{last_user}\"\n\n" if last_user else ""
        return (
            f"{OFFLINE_NOTICE}{body}"
            "Once the key is set, I'll answer as the real model — including code generation, "
            "explanation, fixes and repository search."
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self._reply(messages)))]
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        for token in re.findall(r"\s+|\S+", self._reply(messages)):
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for token in re.findall(r"\s+|\S+", self._reply(messages)):
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))

    def bind_tools(self, tools: Any, **kwargs: Any) -> "OfflineChatModel":
        """No-op tool binding so the agent graph builds without an API key."""
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "_StructuredOffline":
        return _StructuredOffline(schema)


class _StructuredOffline:
    """Returns a default instance of the requested Pydantic schema."""

    def __init__(self, schema: Any) -> None:
        self._schema = schema

    async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
        fields = getattr(self._schema, "model_fields", {})
        if "approved" in fields:
            return self._schema(approved=True, comments=[])
        if "steps" in fields:
            from app.services.agent.graph import PlanStep

            return self._schema(
                steps=[
                    PlanStep(
                        title="Implement goal",
                        description="Implement the requested goal with minimal, safe file edits.",
                        files=[],
                    )
                ]
            )
        try:
            return self._schema()
        except Exception:
            return None


def get_chat_model(provider: str | None = None, temperature: float | None = None) -> BaseMessage:
    """Return a LangChain chat model for the configured provider.

    Supports gemini / deepseek / openrouter / ollama through one interface.
    Falls back to an offline mock model when the provider needs an API key that
    is not set, so the app keeps working without credentials.
    """
    p = (provider or settings.configured_provider).lower()
    temp = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens

    if p == "gemini":
        if not settings.gemini_api_key:
            return OfflineChatModel()
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=temp,
            max_output_tokens=max_tokens or 8192,
            timeout=180,
        )

    if p == "deepseek":
        if not settings.deepseek_api_key:
            return OfflineChatModel()
        return ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=180,
        )

    if p == "openrouter":
        if not settings.openrouter_api_key:
            return OfflineChatModel()
        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temp,
            max_tokens=max_tokens,
            default_headers={"HTTP-Referer": "http://localhost:3000", "X-Title": "AI Engineer"},
            timeout=180,
        )

    if p == "ollama":
        return ChatOpenAI(
            model=settings.ollama_model,
            api_key="ollama",
            base_url=settings.ollama_base_url,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=300,
        )

    raise ValueError(f"Unknown LLM provider: {p}")


def to_langchain_messages(history: list[dict], system: str | None = None) -> list[BaseMessage]:
    """Convert [{role, content}] history to LangChain messages with optional system prefix."""
    messages: list[BaseMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "assistant":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def to_langchain_messages_with_roles(history: list[dict], system: str | None = None) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "")
        from langchain_core.messages import AIMessage

        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages
