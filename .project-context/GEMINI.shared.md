# Geminicli Shared Project Context (v3.2)

You are `geminicli`. We use a **Project Context** memory model for durable collaboration.

> [!IMPORTANT]
> **Hermeticity Rule**: You are a self-contained agent. Never link to files (logs, artifacts) outside `.project-context/`. 
> - If evidence is important: Inline the text into `verification.md` or a commit.
> - If data is large: Copy it to `.project-context/docs/task/active/assets/` before referencing it.

---

## 🛠 MEMORY TIERS

1.  **Project Tier (Permanent)**: Architecture, standards, and "lessons learned" in `docs/project/`.
2.  **Task Tier (Ephemeral)**: Current objective, active summary, verification, and milestone checkpoints in `docs/task/`.

---

## 🚀 SESSION START (/ctx-load)

1.  **Read Worldview**: Read `docs/project/metadata.yaml` and `docs/project/context.md`.
2.  **Read Fast Task View**: Read `docs/task/active/index.md`.
3.  **Activate Skill**: Call `activate_skill(name="context-load")` to reconstruct the task state.
4.  **Greet**: *"Project Context loaded. Tier 1 (Project) and Tier 2 (Task) synchronized. Ready."*

---

## 🛑 SESSION END (/ctx-save)

1.  **Knowledge Extraction**: Did you learn something universal (e.g., a bug pattern or new dependency)?
    - **IF YES**: Update `docs/project/context.md` (Lessons Learned) or `metadata.yaml`.
2.  **Checkpointing**:
    - Always refresh `index.md` and `summary.md`.
    - If a milestone was reached: Call `activate_skill(name="context-checkpoint")`.
3.  **Hermetic Check**: Ensure all references in your write-back are internal to `.project-context/`.

---

## ❌ Constraints
- Do not append to a single log file. Use the Project Context tree.
- Do not create "knowledge debt" by leaving evidence in external `/tmp` or `artifacts/` folders.
