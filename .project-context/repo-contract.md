# Repository Collaboration Contract (v3.2 - Project Context Model)

This contract defines how multiple AI agents (Codex, Antigravity, Claude, geminicli) collaborate using a **Project Context** memory layer.

> [!IMPORTANT]
> **Hermetic Rule**: All project-context records must be self-contained within `.project-context/`. Never link to ephemeral artifacts outside this directory.

---

## 1. The Tiered Memory Tree

The only durable memory for this project is the Project Context tree.

| Tier | Object | Path | Purpose |
|------|--------|------|---------|
| **Project** | **Metadata** | `docs/project/metadata.yaml` | **READ FIRST**. Env, commands, and repo structure. |
| **Project** | **Context** | `docs/project/context.md` | Long-term brain: Architecture, Standards, and History. |
| **Task** | **Index** | `docs/task/active/index.md` | Fast launch view for project switching. |
| **Task** | **Task** | `docs/task/active/task.md` | The current overall objective. |
| **Task** | **Summary** | `docs/task/active/summary.md` | The default resumable image of the current state. |
| **Task** | **Verification** | `docs/task/active/verification.md` | The latest proof-of-work and validation state. |
| **Task** | **Assets** | `docs/task/active/assets/` | Captured evidence (logs/artifacts) for this task. |
| **Task** | **Commits** | `docs/task/active/commits/` | Milestone checkpoints for the main task timeline. |
| **Task** | **Workstreams** | `docs/task/active/workstreams/<name>/` | Optional advanced-mode parallel exploration lanes. |

## 2. Interaction Protocol

### Session Start (/ctx-load)
1. Read Metadata and Project Context first to establish a "worldview."
2. Read `docs/task/active/index.md` for the fastest current-state view.
3. Expand into `task.md`, `summary.md`, and `verification.md` only as needed.

### Session End (/ctx-save)
- **Knowledge Promotion**: If a Session produces universal knowledge (bug fixes, infra patterns), the agent MUST update the **Project Tier** (`context.md`).
- **Hermetic Reference**: Move critical logs/evidence to the `assets/` folder before referencing them in your summary or commit.
- **Checkpointing**: Default to updating the active `summary.md`. Create a structured **Commit** only when a milestone is reached.

## 3. Reasoning Integrity
Do not pollute the active task summary with failed experiments. Use optional **Workstreams** only for exploration, risky prototypes, or genuinely parallel lines of investigation.
