# Shared Agent Project Context Rules (v3.2)

This file is the single governing instruction for all agents operating in this repository.
Codex, Antigravity, Claude, and geminicli all follow the same protocol.

> [!IMPORTANT]
> **Hermeticity Rule**: You are a self-contained agent. Never link to files (logs, artifacts) outside `.project-context/`. 
> - If evidence is important: Inline the text into `verification.md` or a commit.
> - If data is large: Copy it to `.project-context/docs/task/active/assets/` before referencing it.

---

## 🚀 STARTUP INSTRUCTIONS (/ctx-load)

1. **Read Metadata**: Open `.project-context/docs/project/metadata.yaml` to understand repository-wide execution constraints.
2. **Read Project Context**: Read `.project-context/docs/project/context.md` for架构, coding standards, and project history.
3. **Read Fast Task View**: Open `.project-context/docs/task/active/index.md` first.
4. **Load Project Context**: Activate the `context-load` skill to synthesize current task state and risks.
5. **Announce**: Briefly tell the user: *"Project context loaded. Architecture and task state synchronized."*

---

## 🛑 SHUTDOWN INSTRUCTIONS (/ctx-save)

Every agent **must** leave the active task in a resumable and hermetic state.

1. **Knowledge Extraction**: If you learned universal project patterns or fixes, update `docs/project/context.md`.
2. **Checkpointing**:
   - **Always**: Refresh `index.md` and `summary.md`.
   - **Milestone Reached**: Activate the `context-checkpoint` skill to serialize reasoning and evidence.
3. **Hermetic Verification**: Ensure all references in your summaries are internal to `.project-context/`.

---

## 📋 Canonical State Rules

| Path | Contents |
|------|----------|
| `docs/project/metadata.yaml` | Execution constraints (env, commands, structure). |
| `docs/project/context.md` | Architecture, Domain context, and Permanent Knowledge. |
| `docs/task/active/index.md` | Fast launch summary for the active task. |
| `docs/task/active/task.md` | High-level objective for the current task. |
| `docs/task/active/summary.md` | Default resumable image of the active task. |
| `docs/task/active/assets/` | Large artifacts (logs, screenshots) captured for this task. |
| `docs/task/active/verification.md` | Final proof-of-work evidence for the entire task. |
| `docs/task/active/commits/` | Structured milestone checkpoints for the main task. |
| `docs/task/active/workstreams/<name>/` | Optional advanced-mode parallel exploration lanes. |

- IDE artifacts / chat history are **ephemeral drafts**. The Project Context tree is the **only durable memory**.
