from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings


def get_chat_model(provider: str | None = None, temperature: float | None = None) -> BaseMessage:
    """Return a LangChain chat model for the configured provider.

    Supports gemini / deepseek / openrouter / ollama through one interface.
    """
    p = (provider or settings.configured_provider).lower()
    temp = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens

    if p == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to backend/.env or set LLM_PROVIDER to ollama/deepseek/openrouter."
            )
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=temp,
            max_output_tokens=max_tokens or 8192,
            timeout=180,
        )

    if p == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
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
            raise ValueError("OPENROUTER_API_KEY is not set.")
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
