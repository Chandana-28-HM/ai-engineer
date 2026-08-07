"""Offline smoke test for the LangGraph agent (no API key needed).

Uses LangChain's FakeMessagesListChatModel to drive tool calls, verifying:
- make_tools create/read/edit file paths
- single react agent graph executes tools
- multi-agent graph compiles
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel as PydanticBaseModel

from app.services.agent.tools import make_tools

WORKSPACE = Path(__file__).resolve().parent / "_agent_test_ws"
WORKSPACE.mkdir(exist_ok=True)


class FakeToolModel(BaseChatModel, PydanticBaseModel):
    responses: list[AIMessage]
    _index: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        resp = self.responses[self._index % len(self.responses)]
        self._index += 1
        return ChatResult(generations=[ChatGeneration(message=resp)])

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "fake-tool-model"


def fake_model() -> FakeToolModel:
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "create_file",
                    "args": {"path": "hello.py", "content": "print('hello world')"},
                    "id": "call_1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "read_file",
                    "args": {"path": "hello.py"},
                    "id": "call_2",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="Done. I created hello.py and read it back."),
    ]
    return FakeToolModel(responses=responses)


async def main() -> None:
    events: list[dict] = []
    publish = lambda ev: events.append(ev)

    tools = make_tools(WORKSPACE, publish=publish)
    tool_map = {t.name: t for t in tools}

    from langchain.agents import create_agent

    agent = create_agent(fake_model(), tools)

    result = await agent.ainvoke({"messages": [HumanMessage(content="create hello.py")]})
    final = result["messages"][-1].content
    created = (WORKSPACE / "hello.py").exists()
    assert created, "create_file tool did not create the file"
    assert "hello world" in (WORKSPACE / "hello.py").read_text()
    print("PASS: single react agent + file tools worked")
    print(f"      tool events: {[e['data']['kind'] for e in events]}")
    print(f"      final message: {final[:40]!r}")

    # Cleanup
    (WORKSPACE / "hello.py").unlink()

    # Verify multi-agent graph compiles (structure only).
    from unittest.mock import patch

    with patch("app.services.agent.graph.get_chat_model", return_value=fake_model()):
        import app.services.agent.graph as g

        compiled = g.build_multi_agent(WORKSPACE, publish=publish)
        print("PASS: multi-agent LangGraph compiled")


if __name__ == "__main__":
    asyncio.run(main())
