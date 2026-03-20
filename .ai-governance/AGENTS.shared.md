# Shared Agent Governance Rules (v2.1 - GCC Hermetic Model)

This file is the single governing instruction for all agents operating in this repository.
Codex, Antigravity, Claude, and geminicli all follow the same protocol.

> [!IMPORTANT]
> **Hermeticity Rule**: You are a self-contained agent. NEVER link to files (logs, artifacts) outside `.ai-governance/`. 
> - If evidence is important: Inline the text into `verification.md` or a commit.
> - If data is large: Copy it to `.ai-governance/docs/task/active/assets/` before referencing it.

---

## 🚀 STARTUP INSTRUCTIONS (/gov-context)

1. **Read Metadata**: Open `.ai-governance/docs/project/metadata.yaml` to understand repository-wide execution constraints.
2. **Read Project Context**: Read `.ai-governance/docs/project/context.md` for架构, coding standards, and project history.
3. **Load GCC Context**: Activate the `task-context` skill to synthesize current task state and risks.
4. **Announce**: Briefly tell the user: *"GCC Context loaded. Architecture & Task state synchronized."*

---

## 🛑 SHUTDOWN INSTRUCTIONS (/gov-writeback)

Every agent **must** leave the active task in a resumable and hermetic state.

1. **Knowledge Extraction**: If you learned universal project patterns or fixes, update `docs/project/context.md`.
2. **Checkpointing**:
   - **Milestone Reached**: Activate the `task-commit` skill to serialize reasoning and evidence.
   - **Partial Progress**: Update `summary.md` (Current State / Next Action) directly.
3. **Hermetic Verification**: Ensure all references in your summaries are internal to `.ai-governance/`.

---

## 📋 Canonical State Rules

| Path | Contents |
|------|----------|
| `docs/project/metadata.yaml` | Execution constraints (env, commands, structure). |
| `docs/project/context.md` | Architecture, Domain context, and Permanent Knowledge. |
| `docs/task/active/task.md` | High-level objective for the current task. |
| `docs/task/active/assets/` | Large artifacts (logs, screenshots) captured for this task. |
| `docs/task/active/verification.md` | Final proof-of-work evidence for the entire task. |
| `branches/<name>/summary.md` | The "memory image" of the branch. |
| `branches/<name>/commits/` | The structured chain of cognition and decisions. |

- IDE artifacts / chat history are **ephemeral drafts**. The GCC tree is the **only durable memory**.
