from __future__ import annotations

import os
from pathlib import Path

from app.config import settings

# Files we never index or allow the agent to touch.
IGNORED_NAMES = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build",
    ".idea", ".vscode", ".pytest_cache", ".mypy_cache", ".ruff_cache", "storage",
}
IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf", ".zip", ".tar",
    ".gz", ".bin", ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".class", ".jar", ".lock", ".map", ".min.js", ".min.css",
    ".mp4", ".mp3", ".wav", ".woff2",
}
MAX_FILE_BYTES = 500_000


def is_ignored(relative_path: str) -> bool:
    parts = relative_path.replace("\\", "/").split("/")
    if any(part in IGNORED_NAMES for part in parts):
        return True
    ext = Path(relative_path).suffix.lower()
    return ext in IGNORED_EXTENSIONS


def list_files(root: Path, max_depth: int = 10) -> list[Path]:
    files: list[Path] = []
    root = root.resolve()
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            rel = str(entry.path).replace(str(root), "").lstrip("\\/")
            if is_ignored(rel):
                continue
            if entry.is_dir():
                stack.append((Path(entry.path), depth + 1))
            elif entry.is_file():
                try:
                    if entry.stat().st_size <= MAX_FILE_BYTES:
                        files.append(Path(entry.path))
                except OSError:
                    continue
    return files


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def safe_join(workspace: Path, relative_path: str) -> Path:
    """Resolve a path inside workspace and refuse traversal outside of it."""
    target = (workspace.resolve() / relative_path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        raise ValueError(f"Path escapes workspace: {relative_path}")
    return target


def build_file_tree(files: list[str]) -> dict:
    """Build a nested {name, path, type, children} tree from flat relative paths."""
    root: dict = {"name": "", "path": "", "type": "dir", "children": []}

    def find_dir(node: dict, path_parts: list[str]) -> dict:
        current = node
        for part in path_parts:
            found = None
            for child in current["children"]:
                if child["name"] == part:
                    found = child
                    break
            if found is None:
                found = {"name": part, "path": "", "type": "dir", "children": []}
                current["children"].append(found)
            current = found
        return current

    for f in files:
        parts = f.split("/")
        *dirs, filename = parts
        parent = find_dir(root, dirs)
        parent["children"].append({"name": filename, "path": f, "type": "file", "children": []})
    return root["children"]


def language_from_path(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mapping = {
        "py": "python", "ts": "typescript", "tsx": "typescript", "js": "javascript",
        "jsx": "javascript", "go": "go", "rs": "rust", "java": "java", "rb": "ruby",
        "php": "php", "c": "c", "h": "c", "cpp": "cpp", "cc": "cpp", "hpp": "cpp",
        "cs": "csharp", "swift": "swift", "kt": "kotlin", "scala": "scala",
        "sh": "shell", "bash": "shell", "zsh": "shell", "ps1": "powershell",
        "sql": "sql", "html": "html", "css": "css", "scss": "scss", "json": "json",
        "yaml": "yaml", "yml": "yaml", "toml": "toml", "xml": "xml", "md": "markdown",
        "dockerfile": "dockerfile", "makefile": "makefile", "txt": "text",
    }
    basename = os.path.basename(path).lower()
    if basename in ("dockerfile",):
        return "dockerfile"
    if basename in ("makefile",):
        return "makefile"
    return mapping.get(ext, "text")
