from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentRunRequest(BaseModel):
    project_id: int
    conversation_id: int | None = None
    repo_id: int | None = None
    goal: str
    kind: str = "multi"  # single | multi
    agent_mode: bool = True


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    conversation_id: int | None
    repo_id: int | None
    kind: str
    goal: str
    status: str
    summary: str | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    step_index: int
    agent: str
    title: str
    input_text: str
    output_text: str
    files_changed: str | None
    status: str
    created_at: datetime


class AgentRunDetail(AgentRunRead):
    steps: list[AgentStepRead] = []
