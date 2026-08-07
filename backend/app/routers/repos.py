from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Repository
from app.schemas import (
    RepoGitConnect,
    RepoRead,
    RepoStructure,
    SearchRequest,
    SearchResponse,
)
from app.services import repo_service

router = APIRouter(prefix="/api/repos", tags=["repositories"])


@router.get("", response_model=list[RepoRead])
async def list_repos(project_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    result = await db.execute(select(Repository).where(Repository.project_id == project_id).order_by(Repository.created_at.desc()))
    return list(result.scalars())


@router.post("/upload", response_model=RepoRead, status_code=201)
async def upload_repo(
    project_id: int = Form(...),
    name: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        repo = await repo_service.create_repo_from_upload(db, project_id, name, file, file.filename or "repo.zip")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return repo


@router.post("/git", response_model=RepoRead, status_code=201)
async def connect_git(payload: RepoGitConnect, db: AsyncSession = Depends(get_db)):
    repo = await repo_service.create_repo_from_git(db, payload.project_id, payload.url, payload.branch, payload.name)
    if repo.status == "failed":
        raise HTTPException(400, f"Git clone failed: {repo.error}")
    return repo


@router.get("/{repo_id}", response_model=RepoRead)
async def get_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    return repo


@router.post("/{repo_id}/index", response_model=RepoRead)
async def index_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    repo = await repo_service.index_repo(db, repo)
    if repo.status == "failed":
        raise HTTPException(500, f"Indexing failed: {repo.error}")
    return repo


@router.get("/{repo_id}/files", response_model=list[str])
async def repo_files(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    return await repo_service.get_repo_files(repo)


@router.get("/{repo_id}/structure", response_model=RepoStructure)
async def repo_structure(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    return await repo_service.get_structure(db, repo)


@router.post("/{repo_id}/search", response_model=SearchResponse)
async def search_repo(repo_id: int, payload: SearchRequest, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    if repo.status != "indexed":
        raise HTTPException(400, "Repository is not indexed yet. Run indexing first.")
    return await repo_service.search_repo(db, repo, payload.query, limit=payload.limit, answer=True)


@router.delete("/{repo_id}", status_code=204)
async def delete_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    await repo_service.delete_repo(db, repo)
