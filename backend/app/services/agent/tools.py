from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from langchain_core.tools import tool

from app.utils.fs import is_ignored, list_files, relative, safe_join
from app.utils.shell import run_command

PublishFn = Callable[[dict], None]


def make_tools(
    workspace: Path, publish: Optional[PublishFn] = None, changes: Optional[list[str]] = None
) -> list:
    root = workspace.resolve()
    ws = str(root)

    def _track(path: str) -> None:
        if changes is not None:
            rel = relative(root, Path(path))
            if rel not in changes:
                changes.append(rel)

    def _emit(kind: str, data: dict) -> None:
        if publish:
            publish({"event": "agent_tool", "data": {"kind": kind, **data}})

    @tool
    async def list_dir(directory: str = ".") -> str:
        """List files and directories inside the repository. Use to explore the project layout."""
        try:
            target = safe_join(root, directory)
            if not target.is_dir():
                target = target.parent
        except ValueError as exc:
            return f"Error: {exc}"
        files = list_files(target, max_depth=2)
        rel_files = [relative(root, f) for f in files]
        _emit("list_dir", {"directory": directory})
        return "\n".join(rel_files[:200]) if rel_files else "(empty directory)"

    @tool
    async def read_file(path: str) -> str:
        """Read a file inside the repository and return it with line numbers."""
        try:
            target = safe_join(root, path)
            if not target.is_file():
                return f"Error: file not found: {path}"
        except ValueError as exc:
            return f"Error: {exc}"
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        numbered = "\n".join(f"{i + 1:4} | {line}" for i, line in enumerate(lines))
        _emit("read_file", {"path": path, "lines": len(lines)})
        return f"File: {relative(root, target)}\n{numbered}"

    @tool
    async def create_file(path: str, content: str) -> str:
        """Create a new file (or overwrite) inside the repository with the given content."""
        try:
            target = safe_join(root, path)
        except ValueError as exc:
            return f"Error: {exc}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        _emit("create_file", {"path": relative(root, target)})
        _track(str(target))
        return f"Created {relative(root, target)} ({len(content)} chars)"

    @tool
    async def edit_file(path: str, old_string: str, new_string: str) -> str:
        """Replace the first occurrence of old_string with new_string in a repository file."""
        try:
            target = safe_join(root, path)
            if not target.is_file():
                return f"Error: file not found: {path}"
        except ValueError as exc:
            return f"Error: {exc}"
        content = target.read_text(encoding="utf-8", errors="replace")
        if old_string not in content:
            return f"Error: old_string not found in {path}."
        updated = content.replace(old_string, new_string, 1)
        target.write_text(updated, encoding="utf-8")
        _emit("edit_file", {"path": relative(root, target)})
        _track(str(target))
        return f"Edited {relative(root, target)}"

    @tool
    async def run_command(command: str) -> str:
        """Run a shell command inside the repository workspace and return its output."""
        result = await run_command(command, cwd=ws)
        _emit("run_command", {"command": command, "ok": result["ok"]})
        if result["ok"]:
            return result["stdout"] or "(completed with no output)"
        return f"Exit code {result['returncode']}\nSTDOUT:\n{result['stdout']}\nSTDERR:\n{result['stderr']}"

    return [list_dir, read_file, create_file, edit_file, run_command]
