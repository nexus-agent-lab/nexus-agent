from app.tools.sandbox import PythonSandboxTool


def test_python_sandbox_can_use_session_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_DATA_DIR", str(tmp_path))

    tool = PythonSandboxTool()
    result = tool._run(
        "with open('artifact.txt', 'w', encoding='utf-8') as handle:\n"
        "    handle.write('hello from sandbox')\n"
        "with open('artifact.txt', 'r', encoding='utf-8') as handle:\n"
        "    print(handle.read())\n",
        user_id=9,
        session_id=21,
    )

    assert "hello from sandbox" in result
