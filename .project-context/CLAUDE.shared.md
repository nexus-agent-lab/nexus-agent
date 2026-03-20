# Claude Shared Project Context (v3.2)

You are operating in a multi-agent repository using a **Project Context** memory model.

> [!NOTE]
> Project Context records focus on resumable context: what matters now, why it changed, and what should happen next.

---

## 🚀 SESSION START — Do This First

1. **Read Metadata**: Load `.project-context/docs/project/metadata.yaml`. It contains the commands you need to build and test.
2. **Read Active Index**: Load `.project-context/docs/task/active/index.md` for the fastest current-state view.
3. **Execute `context-load`**: Run this skill to reconstruct the task state.
4. **Sync with User**: Tell the user: *"I've read the project context. Status: [status]. Proceeding with [Action]."*

---

## 🛑 SESSION END — Do This Before Stopping

You must leave the repository in a state where another agent can pick up your work without reading the chat history.

1. **Always Refresh Active State**: Update `.project-context/docs/task/active/index.md` and `.project-context/docs/task/active/summary.md`.
2. **Milestone Reached?**: If you completed a feature, fix, or hypothesis test, run `context-checkpoint`.
3. **Evidence**: Write any validation results into the commit or `.project-context/docs/task/active/verification.md`.

---

## ❌ Rules

- **No `progress.md`**: It is deprecated.
- **No `handoff.md`**: Use `summary.md`.
- **Metadata First**: Always check `metadata.yaml` before guessing directory structures or build commands.
- **Durable State**: Only files in `.project-context/docs/` are shared context. Your internal thoughts/artifacts are private to this session.
