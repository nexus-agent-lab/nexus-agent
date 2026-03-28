import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from app.core.decorators import require_role
from app.tools.session_workspace import ensure_session_workspace, resolve_session_path

MAX_RESULTS = 200
MAX_BYTES = 32_000
MAX_LINES = 200


def _sanitize_limit(value: int, default: int, maximum: int) -> int:
    if value <= 0:
        return default
    return min(value, maximum)


def _read_file_portion(path: Path, *, mode: str, lines: int | None = None, max_bytes: int = MAX_BYTES) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        if mode == "read":
            return handle.read(max_bytes)

        content_lines = handle.readlines()
        count = _sanitize_limit(lines or 20, 20, MAX_LINES)
        if mode == "head":
            return "".join(content_lines[:count])
        return "".join(content_lines[-count:])


def _run_rg(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["rg", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return "Error: `rg` is not available in the sandbox environment."
    except subprocess.TimeoutExpired:
        return "Error: search timed out."

    if result.returncode not in (0, 1):
        return f"Error: {result.stderr.strip() or 'rg execution failed'}"
    return result.stdout[:MAX_BYTES] or "(No matches)"


@tool
@require_role("user")
def list_dir(
    path: str = ".",
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    max_results: int = 100,
) -> str:
    """List files in the current session workspace."""
    target = resolve_session_path(user_id, session_id, path)
    if not target.exists():
        return "Error: path does not exist."
    if not target.is_dir():
        return "Error: path is not a directory."

    limit = _sanitize_limit(max_results, 100, MAX_RESULTS)
    entries = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:limit]:
        kind = "dir" if item.is_dir() else "file"
        size = item.stat().st_size if item.is_file() else 0
        entries.append(f"{kind}\t{size}\t{item.name}")
    return "\n".join(entries) or "(Empty directory)"


@tool
@require_role("user")
def find_files(
    path: str = ".",
    glob: Optional[str] = None,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    max_results: int = 100,
) -> str:
    """Find files inside the current session workspace."""
    root = resolve_session_path(user_id, session_id, path)
    if not root.exists():
        return "Error: path does not exist."
    if not root.is_dir():
        return "Error: path is not a directory."

    limit = _sanitize_limit(max_results, 100, MAX_RESULTS)
    pattern = glob or "**/*"
    matches = []
    for item in root.glob(pattern):
        if item.is_file():
            matches.append(str(item.relative_to(ensure_session_workspace(user_id, session_id))))
        if len(matches) >= limit:
            break
    return "\n".join(matches) or "(No files found)"


@tool
@require_role("user")
def grep_text(
    pattern: str,
    path: str = ".",
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    max_results: int = 50,
    context_lines: int = 1,
) -> str:
    """Search text with ripgrep inside the current session workspace."""
    root = resolve_session_path(user_id, session_id, path)
    if not root.exists():
        return "Error: path does not exist."

    limit = _sanitize_limit(max_results, 50, MAX_RESULTS)
    context = _sanitize_limit(context_lines, 1, 5)
    args = [
        "--line-number",
        "--hidden",
        "--max-count",
        str(limit),
        "--context",
        str(context),
        pattern,
        str(root),
    ]
    return _run_rg(args, cwd=ensure_session_workspace(user_id, session_id))


@tool
@require_role("user")
def read_file(
    path: str,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    max_bytes: int = MAX_BYTES,
) -> str:
    """Read a file from the current session workspace."""
    target = resolve_session_path(user_id, session_id, path)
    if not target.exists() or not target.is_file():
        return "Error: file does not exist."
    return _read_file_portion(target, mode="read", max_bytes=_sanitize_limit(max_bytes, MAX_BYTES, MAX_BYTES))


@tool
@require_role("user")
def head_file(
    path: str,
    lines: int = 20,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
) -> str:
    """Read the first lines of a file from the current session workspace."""
    target = resolve_session_path(user_id, session_id, path)
    if not target.exists() or not target.is_file():
        return "Error: file does not exist."
    return _read_file_portion(target, mode="head", lines=lines)


@tool
@require_role("user")
def tail_file(
    path: str,
    lines: int = 20,
    *,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
) -> str:
    """Read the last lines of a file from the current session workspace."""
    target = resolve_session_path(user_id, session_id, path)
    if not target.exists() or not target.is_file():
        return "Error: file does not exist."
    return _read_file_portion(target, mode="tail", lines=lines)
