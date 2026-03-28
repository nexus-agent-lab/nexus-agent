import os
import shutil
import time
from pathlib import Path


def get_sandbox_data_dir() -> Path:
    return Path(os.getenv("SANDBOX_DATA_DIR", "/app/storage/sandbox_data"))


def get_user_root(user_id: int | None) -> Path:
    safe_user = str(user_id or "anonymous")
    return get_sandbox_data_dir() / "users" / safe_user


def get_session_workspace(user_id: int | None, session_id: int | None) -> Path:
    safe_session = str(session_id or "shared")
    return get_user_root(user_id) / "sessions" / safe_session


def ensure_session_workspace(user_id: int | None, session_id: int | None) -> Path:
    root = get_session_workspace(user_id, session_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_session_path(user_id: int | None, session_id: int | None, relative_path: str | None) -> Path:
    workspace = ensure_session_workspace(user_id, session_id).resolve()
    requested = (workspace / (relative_path or ".")).resolve()

    if requested != workspace and workspace not in requested.parents:
        raise ValueError("Path escapes current session workspace")

    return requested


def delete_session_workspace(user_id: int | None, session_id: int | None) -> bool:
    workspace = get_session_workspace(user_id, session_id)
    if not workspace.exists():
        return False

    shutil.rmtree(workspace, ignore_errors=False)

    sessions_root = workspace.parent
    user_root = sessions_root.parent

    if sessions_root.exists() and not any(sessions_root.iterdir()):
        sessions_root.rmdir()
    if user_root.exists() and not any(user_root.iterdir()):
        user_root.rmdir()

    return True


def _workspace_latest_mtime(path: Path) -> float:
    latest = path.stat().st_mtime
    for child in path.rglob("*"):
        try:
            latest = max(latest, child.stat().st_mtime)
        except FileNotFoundError:
            continue
    return latest


def cleanup_stale_session_workspaces(
    *,
    max_age_hours: int,
    dry_run: bool = True,
    now: float | None = None,
) -> dict[str, object]:
    users_root = get_sandbox_data_dir() / "users"
    current_time = now if now is not None else time.time()
    cutoff = current_time - (max_age_hours * 3600)

    scanned = 0
    removed = 0
    removed_paths: list[str] = []

    if not users_root.exists():
        return {"scanned": scanned, "removed": removed, "removed_paths": removed_paths}

    for session_dir in users_root.glob("*/sessions/*"):
        if not session_dir.is_dir():
            continue
        scanned += 1
        latest_mtime = _workspace_latest_mtime(session_dir)
        if latest_mtime > cutoff:
            continue

        removed_paths.append(str(session_dir))
        if dry_run:
            continue

        shutil.rmtree(session_dir, ignore_errors=False)
        removed += 1

        sessions_root = session_dir.parent
        user_root = sessions_root.parent
        if sessions_root.exists() and not any(sessions_root.iterdir()):
            sessions_root.rmdir()
        if user_root.exists() and not any(user_root.iterdir()):
            user_root.rmdir()

    return {"scanned": scanned, "removed": removed, "removed_paths": removed_paths}
