from __future__ import annotations

import asyncio
import re

from app.config import settings

# Block obviously dangerous / destructive commands.
BLOCKED_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\brm\s+-rf\s+~",
    r"\brm\s+-rf\s+(\*|\.\*)\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bformat\b.*\b(C:|D:)",
    r"\bdel\b.*\b/system32",
    r"\bformat\b",
    r":\(\)\s*\{[^}]*\}",
]


def is_blocked(command: str) -> bool:
    return any(re.search(p, command, re.IGNORECASE) for p in BLOCKED_PATTERNS)


async def run_command(command: str, cwd: str, timeout: int | None = None) -> dict:
    """Run a shell command safely with a timeout and captured output."""
    if is_blocked(command):
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "Command blocked by safety policy."}

    timeout = timeout or settings.command_timeout_seconds

    # On Windows prefer running through cmd; on POSIX use sh.
    if __import__("sys").platform == "win32":
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
    else:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace")[-12000:],
            "stderr": stderr.decode("utf-8", errors="replace")[-12000:],
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": f"Command timed out after {timeout}s."}
