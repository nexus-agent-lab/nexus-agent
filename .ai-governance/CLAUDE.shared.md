# Claude Shared Governance (v2.1 - GCC Memory Model)

You are operating in a multi-agent repository using a **Git-Context-Controller (GCC)** memory model.

> [!NOTE]
> GCC records are focus on "Cognitive History" (why/how). They are separate from the Git repository's version history, though you should strive to keep them synchronized when making code changes.

---

## 🚀 SESSION START — Do This First

1. **Read Metadata**: Load `.ai-governance/docs/project/metadata.yaml`. It contains the commands you need to build and test.
2. **Execute `task-context`**: Run this skill to reconstruct the task state.
3. **Sync with User**: Tell the user: *"I've read the GCC context. Branch: [name]. Status: [status]. Proceeding with [Action]."*

---

## 🛑 SESSION END — Do This Before Stopping

You must leave the repository in a state where another agent can pick up your work without reading the chat history.

1. **Milestone Reached?**: If you completed a feature, fix, or hypothesis test, run `task-commit`.
2. **Small Session?**: If you only did research or minor edits, update `.ai-governance/docs/task/active/branches/[branch]/summary.md` directly. Update `Current State` and `Next Action`.
3. **Evidence**: Write any validation results into the commit or the global `verification.md`.

---

## ❌ Rules

- **No `progress.md`**: It is deprecated.
- **No `handoff.md`**: Use `summary.md`.
- **Metadata First**: Always check `metadata.yaml` before guessing directory structures or build commands.
- **Durable State**: Only files in `.ai-governance/docs/` are shared context. Your internal thoughts/artifacts are private to this session.
