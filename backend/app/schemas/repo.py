from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RepoCreate(BaseModel):
    project_id: int
    name: str = ""


class RepoGitConnect(BaseModel):
    project_id: int
    url: str
    branch: str | None = None
    name: str = ""


class RepoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    source: str
    remote_url: str | None
    local_path: str
    status: str
    error: str | None
    file_count: int
    indexed_chunks: int
    created_at: datetime
    updated_at: datetime


class RepoFileNode(BaseModel):
    path: str
    type: str  # file | dir
    children: list["RepoFileNode"] = []


class RepoStructure(BaseModel):
    summary: str
    language_stats: dict[str, int]
    dependency_files: list[str]
    file_tree: RepoFileNode


class SearchRequest(BaseModel):
    repo_id: int
    query: str
    limit: int = 5


class SearchSource(BaseModel):
    file_path: str
    score: float
    snippet: str
    line: int


class SearchResponse(BaseModel):
    query: str
    results: list[SearchSource]
    answered: str = ""
