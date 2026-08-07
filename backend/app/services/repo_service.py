from __future__ import annotations

import asyncio
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CodeChunk, Repository
from app.schemas.repo import SearchResponse, SearchSource
from app.services.llm.embeddings import embedder
from app.services.llm.factory import get_chat_model
from app.services.llm.prompts import CODE_SEARCH
from app.services.vector_store import vector_store
from app.utils.fs import build_file_tree, is_ignored, language_from_path, list_files, relative
from app.utils.fs import MAX_FILE_BYTES

CHUNK_LINES = 60
CHUNK_OVERLAP = 6


def sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "repo"


def workspace_path(project_id: int, repo_id: int) -> Path:
    path = settings.workspaces_dir / str(project_id) / str(repo_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def create_repo_from_upload(
    db: AsyncSession, project_id: int, name: str, file: object, filename: str
) -> Repository:
    """Save an uploaded zip and extract it into the repo workspace."""
    from app.models import Project

    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found")

    repo_name = sanitize_name(name or Path(filename).stem)
    repo = Repository(
        project_id=project_id,
        name=repo_name,
        source="upload",
        status="created",
        local_path=str(workspace_path(project_id, 0)),
    )
    db.add(repo)
    await db.flush()
    repo.local_path = str(workspace_path(project_id, repo.id))
    await db.flush()

    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        raise ValueError("Zip file exceeds 50MB limit")

    root = workspace_path(project_id, repo.id)
    # Clear just in case a previous extraction exists
    for item in root.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)

    with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            name_part = member.filename.replace("\\", "/")
            if is_ignored(name_part):
                continue
            target = (root / name_part).resolve()
            if not str(target).startswith(str(root.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.file_size > MAX_FILE_BYTES:
                continue
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)

    repo.file_count = len(list_files(root))
    await db.commit()
    await db.refresh(repo)
    return repo


async def create_repo_from_git(
    db: AsyncSession, project_id: int, url: str, branch: str | None, name: str
) -> Repository:
    """Clone a git repository into the workspace."""
    from app.models import Project

    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found")

    repo_name = sanitize_name(name or re.sub(r"\.git$", "", Path(url).stem))
    repo = Repository(
        project_id=project_id,
        name=repo_name,
        source="git",
        remote_url=url,
        status="indexing",
        local_path=str(workspace_path(project_id, 0)),
    )
    db.add(repo)
    await db.flush()
    root = workspace_path(project_id, repo.id)
    repo.local_path = str(root)
    await db.flush()

    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(root)]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace"))
        repo.status = "created"
        repo.file_count = len(list_files(root))
        await db.commit()
        await db.refresh(repo)
        return repo
    except Exception as exc:  # noqa: BLE001
        repo.status = "failed"
        repo.error = str(exc)
        await db.commit()
        await db.refresh(repo)
        return repo


def chunk_lines(content: str) -> list[tuple[int, int, str]]:
    """Split file content into overlapping line chunks."""
    lines = content.splitlines()
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(lines):
        end = min(start + CHUNK_LINES, len(lines))
        chunks.append((start + 1, end, "\n".join(lines[start:end])))
        if end >= len(lines):
            break
        start = end - CHUNK_OVERLAP
    return chunks


async def index_repo(db: AsyncSession, repo: Repository) -> Repository:
    """Parse files, chunk, embed and index into Qdrant + DB."""
    repo.status = "indexing"
    await db.commit()

    root = Path(repo.local_path)
    files = list_files(root)
    payloads: list[dict] = []
    texts: list[str] = []
    db_chunks: list[CodeChunk] = []

    try:
        for file_path in files:
            rel = relative(root, file_path)
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not content.strip():
                continue
            language = language_from_path(rel)
            chunks = chunk_lines(content)
            for idx, (s_line, e_line, text) in enumerate(chunks):
                texts.append(text)
                payloads.append(
                    {
                        "file_path": rel,
                        "language": language,
                        "chunk_index": idx,
                        "content": text,
                        "start_line": s_line,
                        "end_line": e_line,
                    }
                )
                db_chunks.append(
                    CodeChunk(
                        repo_id=repo.id,
                        file_path=rel,
                        language=language,
                        chunk_index=idx,
                        content=text,
                        start_line=s_line,
                        end_line=e_line,
                    )
                )

        # Remove any stale chunks then batch insert new ones.
        await db.execute(delete(CodeChunk).where(CodeChunk.repo_id == repo.id))
        db.add_all(db_chunks)
        await db.commit()

        if texts:
            vectors = await embedder().embed_texts(texts)
            await vector_store.delete_repo(repo.id)
            indexed = await vector_store.upsert(repo.id, vectors, payloads)
            repo.indexed_chunks = indexed
        else:
            repo.indexed_chunks = 0

        repo.status = "indexed"
        repo.error = None
    except Exception as exc:  # noqa: BLE001
        repo.status = "failed"
        repo.error = str(exc)
    finally:
        await db.commit()
        await db.refresh(repo)
    return repo


async def delete_repo(db: AsyncSession, repo: Repository) -> None:
    await vector_store.delete_repo(repo.id)
    await db.delete(repo)
    await db.commit()


async def get_repo_files(repo: Repository) -> list[str]:
    root = Path(repo.local_path)
    return [relative(root, f) for f in list_files(root)]


def dependency_files(tree: list[str]) -> list[str]:
    names = {
        "package.json": "Node.js / JavaScript",
        "requirements.txt": "Python (pip)",
        "pyproject.toml": "Python (pyproject)",
        "poetry.lock": "Python (Poetry)",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java (Gradle)",
        "composer.json": "PHP",
        "Gemfile": "Ruby",
        "Pipfile": "Python (Pipenv)",
        "setup.py": "Python (setuptools)",
        "pubspec.yaml": "Dart/Flutter",
        "mix.exs": "Elixir",
        "package-lock.json": "Node.js lockfile",
        "uv.lock": "Python (uv)",
    }
    found: list[str] = []
    for tree_path in tree:
        base = Path(tree_path).name
        if base in names:
            found.append(f"{tree_path}  ({names[base]})")
    return found


async def structure_summary(repo: Repository, tree: list[str], language_stats: dict[str, int]) -> str:
    """Use the LLM to summarize the repository structure (best-effort)."""
    stats = ", ".join(f"{lang}: {count}" for lang, count in sorted(language_stats.items(), key=lambda x: -x[1]))
    sample = "\n".join(tree[:80])
    prompt = (
        "Summarize this software repository in under 120 words for a developer: "
        f"what kind of project it is, its architecture and main entry points.\n\n"
        f"Languages: {stats}\nFile tree (first 80):\n{sample}"
    )
    try:
        from langchain_core.messages import HumanMessage

        model = get_chat_model()
        response = await model.ainvoke([HumanMessage(content=prompt)])
        return str(response.content).strip()
    except Exception:  # noqa: BLE001
        return f"Repository with {len(tree)} files. Primary languages: {stats or 'n/a'}."


async def get_structure(db: AsyncSession, repo: Repository) -> dict:
    tree = await get_repo_files(repo)
    language_stats = Counter(language_from_path(p) for p in tree)
    deps = dependency_files(tree)
    summary = await structure_summary(repo, tree, dict(language_stats))
    return {
        "summary": summary,
        "language_stats": dict(language_stats),
        "dependency_files": deps,
        "file_tree": build_file_tree(tree),
    }


async def search_repo(
    db: AsyncSession, repo: Repository, query: str, limit: int = 5, answer: bool = True
) -> SearchResponse:
    query_vector = await embedder().embed_query(query)
    hits = await vector_store.search(repo.id, query_vector, limit=limit)
    sources = [
        SearchSource(
            file_path=h["file_path"],
            score=h["score"],
            snippet=h["content"],
            line=h["start_line"],
        )
        for h in hits
    ]

    answered = ""
    if answer and hits:
        try:
            from app.services.llm.prompts import rag_context

            from langchain_core.messages import HumanMessage

            context = rag_context(
                [
                    {
                        "file_path": h["file_path"],
                        "line": h["start_line"],
                        "snippet": h["content"],
                    }
                    for h in hits
                ]
            )
            model = get_chat_model()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": CODE_SEARCH},
                    {"role": "user", "content": f"{context}\n\nQuestion: {query}"},
                ]
            )
            answered = str(response.content).strip()
        except Exception:  # noqa: BLE001
            answered = ""

    return SearchResponse(query=query, results=sources, answered=answered)
