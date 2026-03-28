from app.tools.inspector_tools import find_files, grep_text, head_file, list_dir, read_file, tail_file
from app.tools.session_workspace import ensure_session_workspace, resolve_session_path


def test_resolve_session_path_blocks_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_DATA_DIR", str(tmp_path))

    root = ensure_session_workspace(7, 11)
    assert root.exists()

    try:
        resolve_session_path(7, 11, "../other")
        assert False, "Expected path escape to fail"
    except ValueError:
        pass


def test_inspector_tools_are_session_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_DATA_DIR", str(tmp_path))

    session_root = ensure_session_workspace(7, 11)
    nested = session_root / "logs"
    nested.mkdir(parents=True, exist_ok=True)
    target = nested / "app.log"
    target.write_text("alpha\nbeta\nneedle\ngamma\n", encoding="utf-8")

    listing = list_dir.func(path=".", user_id=7, session_id=11)
    assert "logs" in listing

    found = find_files.func(path=".", glob="**/*.log", user_id=7, session_id=11)
    assert "logs/app.log" in found

    grepped = grep_text.func("needle", path=".", user_id=7, session_id=11)
    assert "needle" in grepped

    content = read_file.func("logs/app.log", user_id=7, session_id=11)
    assert "alpha" in content
    assert "needle" in content

    assert "alpha" in head_file.func("logs/app.log", lines=1, user_id=7, session_id=11)
    assert "gamma" in tail_file.func("logs/app.log", lines=1, user_id=7, session_id=11)
