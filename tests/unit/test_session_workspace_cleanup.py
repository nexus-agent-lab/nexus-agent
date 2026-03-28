import os
import time

import pytest
from sqlalchemy import select

from app.core.session import SessionManager
from app.models.session import Session, SessionMessage, SessionSummary
from app.models.user import User
from app.tools.session_workspace import cleanup_stale_session_workspaces, ensure_session_workspace


@pytest.mark.asyncio
async def test_clear_history_removes_session_workspace_and_summaries(test_db, monkeypatch):
    monkeypatch.setenv("SANDBOX_DATA_DIR", os.path.join(os.getcwd(), "tests", "tmp", "sandbox_clear_history"))

    user = User(username="workspace-user", role="user", api_key="workspace-key")
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    session = Session(user_id=user.id, session_uuid="session-clear-history", active=True, title="Reset Me")
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    workspace = ensure_session_workspace(user.id, session.id)
    artifact = workspace / "tool_output.txt"
    artifact.write_text("stale data", encoding="utf-8")

    await SessionManager.save_message(session.id, "user", "human", "hello")
    test_db.add(SessionSummary(session_id=session.id, summary="summary", start_msg_id=1, end_msg_id=1, msg_count=1))
    await test_db.commit()

    await SessionManager.clear_history(session.id)

    remaining_messages = (
        (await test_db.execute(select(SessionMessage).where(SessionMessage.session_id == session.id))).scalars().all()
    )
    remaining_summaries = (
        (await test_db.execute(select(SessionSummary).where(SessionSummary.session_id == session.id))).scalars().all()
    )

    assert remaining_messages == []
    assert remaining_summaries == []
    assert not workspace.exists()


def test_cleanup_stale_session_workspaces_removes_old_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_DATA_DIR", str(tmp_path))

    old_workspace = ensure_session_workspace(7, 11)
    old_file = old_workspace / "artifact.txt"
    old_file.write_text("old", encoding="utf-8")

    new_workspace = ensure_session_workspace(7, 12)
    new_file = new_workspace / "artifact.txt"
    new_file.write_text("new", encoding="utf-8")

    now = time.time()
    old_timestamp = now - (72 * 3600)
    os.utime(old_workspace, (old_timestamp, old_timestamp))
    os.utime(old_file, (old_timestamp, old_timestamp))

    dry_run = cleanup_stale_session_workspaces(max_age_hours=24, dry_run=True, now=now)
    assert dry_run["scanned"] == 2
    assert str(old_workspace) in dry_run["removed_paths"]
    assert old_workspace.exists()

    result = cleanup_stale_session_workspaces(max_age_hours=24, dry_run=False, now=now)
    assert result["removed"] == 1
    assert str(old_workspace) in result["removed_paths"]
    assert not old_workspace.exists()
    assert new_workspace.exists()
