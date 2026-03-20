# Repository Collaboration Contract (v3.0 - GCC Hermetic Model)

This contract defines how multiple AI agents (Codex, Antigravity, Claude, geminicli) collaborate using a **Git-Context-Controller (GCC)** memory layer.

> [!IMPORTANT]
> **Hermetic Rule**: All governance records must be self-contained within `.ai-governance/`. Never link to ephemeral artifacts outside this directory.

---

## 1. The Tiered Memory Tree

The only durable memory for this project is the GCC tree.

| Tier | Object | Path | Purpose |
|------|--------|------|---------|
| **Project** | **Metadata** | `docs/project/metadata.yaml` | **READ FIRST**. Env, commands, and repo structure. |
| **Project** | **Context** | `docs/project/context.md` | Long-term brain: Architecture, Standards, and History. |
| **Task** | **Task** | `docs/task/active/task.md` | The current overall objective. |
| **Task** | **Assets** | `docs/task/active/assets/` | Captured evidence (logs/artifacts) for this task. |
| **Task** | **Summary** | `branches/<name>/summary.md` | The "resumable image" of the current state. |
| **Task** | **Commits** | `branches/<name>/commits/` | The history of intent and decisions. |

## 2. Interaction Protocol

### Session Start (/gov-context)
1. Read Metadata and Project Context first to establish a "worldview."
2. Synthesize the Task state to build a mental model of current progress and risks.

### Session End (/gov-writeback)
- **Knowledge Promotion**: If a Session produces universal knowledge (bug fixes, infra patterns), the agent MUST update the **Project Tier** (`context.md`).
- **Hermetic Reference**: Move critical logs/evidence to the `assets/` folder before referencing them in your summary or commit.
- **Checkpointing**: Decide whether to create a structured **Commit** or just update the **Summary** based on work achieved.

## 3. Reasoning Integrity
Do not pollute the `main` branch with failed experiments. Use **Task Branches** (isolated reasoning folders) for exploration or radical changes.
