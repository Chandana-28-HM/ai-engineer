from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    project_id: int | None = None
    repo_id: int | None = None
    message: str = Field(min_length=1)


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class IntentRequest(BaseModel):
    message: str


class IntentResponse(BaseModel):
    intent: str
    needs_repo: bool = False


class CodeTaskRequest(BaseModel):
    """Direct code task (generate / explain / fix) invoked from UI actions."""

    message: str = Field(min_length=1)
    conversation_id: int | None = None
    project_id: int | None = None
    repo_id: int | None = None
    task_type: str = "generate"  # generate | explain | fix | chat
