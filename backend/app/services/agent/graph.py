from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

try:
    from langchain.agents import create_agent
except ImportError:  # pragma: no cover
    from langgraph.prebuilt import create_react_agent as create_agent

from app.config import settings
from app.services.agent.tools import PublishFn, make_tools
from app.services.llm import prompts
from app.services.llm.factory import get_chat_model

MAX_STEPS = 8


class ReviewVerdict(BaseModel):
    approved: bool
    comments: list[str]


class PlanStep(BaseModel):
    title: str
    description: str
    files: list[str]


class Plan(BaseModel):
    steps: list[PlanStep]


def make_single_agent(workspace: Path, publish: Optional[PublishFn] = None, changes: Optional[list[str]] = None):
    """LangGraph ReAct agent with repository file/shell tools."""
    tools = make_tools(workspace, publish=publish, changes=changes)
    model = get_chat_model()
    system = f"{prompts.CODER}\n\nWorkspace: {workspace.resolve()}\nAll file operations must stay inside this workspace."
    return create_agent(model, tools, system_prompt=system)


async def _stream_agent(agent: Any, instruction: str, publish: Optional[PublishFn]) -> str:
    """Invoke a react agent and stream its text tokens as events."""
    full = ""
    async for event in agent.astream_events(
        {"messages": [HumanMessage(content=instruction)]}, version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and getattr(chunk, "content", None):
                piece = chunk.content
                if isinstance(piece, list):
                    piece = "".join(p.get("text", "") for p in piece if isinstance(p, dict))
                if piece:
                    full += piece
                    if publish:
                        publish({"event": "agent_token", "data": {"text": piece}})
    return full


async def _file_contents(workspace: Path, files: list[str]) -> str:
    parts: list[str] = []
    for f in files[:15]:
        target = (workspace.resolve() / f).resolve()
        if not str(target).startswith(str(workspace.resolve())):
            continue
        try:
            parts.append(f"### {f}\n```\n{target.read_text(encoding='utf-8', errors='replace')[:8000]}\n```")
        except OSError:
            continue
    return "\n\n".join(parts)


class MultiAgentState(TypedDict):
    goal: str
    structure: str
    file_list: str
    plan: list[dict]
    current_step: int
    implementation: list[str]
    step_files: list[str]
    review_approved: bool
    review_comments: list[str]
    debug_loop: int
    final_docs: str


def build_multi_agent(workspace: Path, publish: Optional[PublishFn] = None):
    model = get_chat_model()
    root = workspace.resolve()

    async def planner_node(state: MultiAgentState) -> dict:
        context = prompts.goal_context(structure=state.get("structure"), tree=(state.get("file_list") or "").splitlines()[:60])
        prompt = f"{prompts.PLANNER}\n\n{context}\n\nGOAL:\n{state['goal']}"
        if publish:
            publish({"event": "step", "data": {"agent": "planner", "title": "Planning the work", "status": "running"}})
        try:
            planner_model = model.with_structured_output(Plan)
            result: Plan = await planner_model.ainvoke([SystemMessage(content=prompt)])
            steps = [step.model_dump() for step in result.steps][:MAX_STEPS]
            if publish:
                publish({"event": "step", "data": {"agent": "planner", "title": "Planning the work", "status": "done", "plan": steps}})
            return {"plan": steps, "current_step": 0}
        except Exception as exc:  # noqa: BLE001
            if publish:
                publish({"event": "error", "data": {"message": f"Planner failed: {exc}"}})
            # Fallback: single implicit step so the run can continue.
            return {"plan": [{"title": "Implement goal", "description": state["goal"], "files": []}], "current_step": 0}

    async def coder_node(state: MultiAgentState) -> dict:
        step = state["plan"][state["current_step"]]
        idx = state["current_step"]
        total = len(state["plan"])
        title = f"Step {idx + 1}/{total}: {step['title']}"
        if publish:
            publish({"event": "step", "data": {"agent": "coder", "title": title, "status": "running"}})
        instruction = (
            f"GOAL: {state['goal']}\n\n"
            f"{title}\n{step['description']}\n"
            f"Files involved: {', '.join(step.get('files', []) or [])}\n\n"
            "Implement this step now. Read relevant files first, then make minimal edits. Run commands to verify if useful."
        )
        changes: list[str] = []
        agent = make_single_agent(root, publish=publish, changes=changes)
        summary = await _stream_agent(agent, instruction, publish)
        if publish:
            publish({"event": "step", "data": {"agent": "coder", "title": title, "status": "done", "files": changes, "output": summary[-1500:]}})
        return {
            "implementation": state["implementation"] + [f"{title}\n{summary}"],
            "step_files": changes,
            "review_approved": False,
            "review_comments": [],
        }

    async def reviewer_node(state: MultiAgentState) -> dict:
        step = state["plan"][state["current_step"]]
        idx = state["current_step"]
        title = f"Review step {idx + 1}: {step['title']}"
        if publish:
            publish({"event": "step", "data": {"agent": "reviewer", "title": title, "status": "running"}})
        contents = await _file_contents(root, state.get("step_files") or [])
        prompt = (
            f"{prompts.REVIEWER}\n\nGOAL: {state['goal']}\n\n"
            f"STEP: {step['title']}\n{step['description']}\n\n"
            f"Changed files for this step:\n{contents or '(no file changes recorded)'}\n\n"
            "Review the implementation against the step description. Respond ONLY with JSON {approved, comments}."
        )
        try:
            reviewer_model = model.with_structured_output(ReviewVerdict)
            verdict: ReviewVerdict = await reviewer_model.ainvoke([SystemMessage(content=prompt)])
            if publish:
                publish({
                    "event": "step",
                    "data": {
                        "agent": "reviewer",
                        "title": title,
                        "status": "done",
                        "approved": verdict.approved,
                        "comments": verdict.comments,
                    },
                })
            return {"review_approved": verdict.approved, "review_comments": verdict.comments}
        except Exception as exc:  # noqa: BLE001
            if publish:
                publish({"event": "error", "data": {"message": f"Reviewer failed: {exc}"}})
            return {"review_approved": True, "review_comments": []}

    async def debugger_node(state: MultiAgentState) -> dict:
        step = state["plan"][state["current_step"]]
        idx = state["current_step"]
        title = f"Fix issues in step {idx + 1}: {step['title']}"
        if publish:
            publish({"event": "step", "data": {"agent": "debugger", "title": title, "status": "running"}})
        contents = await _file_contents(root, state.get("step_files") or [])
        comments = "\n".join(f"- {c}" for c in state.get("review_comments", []))
        instruction = (
            f"GOAL: {state['goal']}\n\nSTEP: {step['title']}\n{step['description']}\n\n"
            f"Reviewer comments:\n{comments or '- none'}\n\n"
            f"Relevant files:\n{contents or '(none)'}\n\n"
            "Fix the reported issues with minimal, safe edits. Then summarize what you changed."
        )
        changes: list[str] = []
        agent = make_single_agent(root, publish=publish, changes=changes)
        summary = await _stream_agent(agent, instruction, publish)
        if publish:
            publish({"event": "step", "data": {"agent": "debugger", "title": title, "status": "done", "files": changes, "output": summary[-1500:]}})
        return {
            "implementation": state["implementation"] + [f"{title}\n{summary}"],
            "step_files": state.get("step_files") or [],
            "debug_loop": state.get("debug_loop", 0) + 1,
            "review_approved": False,
            "review_comments": [],
        }

    async def documenter_node(state: MultiAgentState) -> dict:
        if publish:
            publish({"event": "step", "data": {"agent": "documenter", "title": "Writing documentation", "status": "running"}})
        steps_done = "\n\n".join(state.get("implementation", []) or ["(no steps completed)"])
        prompt = (
            f"{prompts.DOCUMENTER}\n\nGOAL: {state['goal']}\n\n"
            f"WORK COMPLETED:\n{steps_done}\n\n"
            f"PROJECT FILES (partial):\n{'\n'.join((state.get('file_list') or '').splitlines()[:40])}\n\n"
            "Write the markdown document now."
        )
        try:
            response = await model.ainvoke([SystemMessage(content=prompt)])
            docs = str(response.content).strip()
            target = root / "AGENT_REPORT.md"
            target.write_text(f"# Agent Execution Report\n\n{docs}\n", encoding="utf-8")
            if publish:
                publish({"event": "step", "data": {"agent": "documenter", "title": "Writing documentation", "status": "done", "files": ["AGENT_REPORT.md"]}})
            return {"final_docs": docs}
        except Exception as exc:  # noqa: BLE001
            if publish:
                publish({"event": "error", "data": {"message": f"Documenter failed: {exc}"}})
            return {"final_docs": f"(Documentation failed: {exc})"}

    graph = StateGraph(MultiAgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("documenter", documenter_node)
    graph.add_node("advance", lambda state: {"current_step": state["current_step"] + 1})

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "reviewer")

    def after_review(state: MultiAgentState) -> str:
        if state.get("review_approved"):
            return "advance"
        if state.get("debug_loop", 0) < settings.agent_max_review_loops:
            return "debug"
        return "advance"

    graph.add_conditional_edges("reviewer", after_review, {"debug": "debugger", "advance": "advance"})
    graph.add_edge("debugger", "reviewer")

    def should_advance(state: MultiAgentState) -> str:
        if state["current_step"] + 1 < len(state.get("plan", [])):
            return "coder"
        return "documenter"

    graph.add_conditional_edges("advance", should_advance, {"coder": "coder", "documenter": "documenter"})
    graph.add_edge("documenter", END)

    return graph.compile()


async def run_single_agent(workspace: Path, goal: str, publish: Optional[PublishFn] = None) -> str:
    agent = make_single_agent(workspace, publish=publish)
    return await _stream_agent(agent, goal, publish)


async def run_multi_agent(workspace: Path, goal: str, publish: Optional[PublishFn] = None) -> dict:
    from app.utils.fs import list_files, relative

    file_list = [relative(workspace, f) for f in list_files(workspace)]
    graph = build_multi_agent(workspace, publish)
    result = await graph.ainvoke(
        {
            "goal": goal,
            "structure": "",
            "file_list": "\n".join(file_list[:200]),
            "plan": [],
            "current_step": 0,
            "implementation": [],
            "step_files": [],
            "review_approved": False,
            "review_comments": [],
            "debug_loop": 0,
            "final_docs": "",
        }
    )
    return result
