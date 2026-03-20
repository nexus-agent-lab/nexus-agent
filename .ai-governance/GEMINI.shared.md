# Geminicli Shared Governance (v2.1 - GCC Hermetic Model)

You are `geminicli`. We use a **Git-Context-Controller (GCC)** memory model for durable collaboration.

> [!IMPORTANT]
> **Hermeticity Rule**: You are a self-contained agent. NEVER link to files (logs, artifacts) outside `.ai-governance/`. 
> - If evidence is important: Inline the text into `verification.md` or a commit.
> - If data is large: Copy it to `.ai-governance/docs/task/active/assets/` before referencing it.

---

## 🛠 MEMORY TIERS

1.  **Project Tier (Permanent)**: Architecture, standards, and "lessons learned" in `docs/project/`.
2.  **Task Tier (Ephemeral)**: Current objective, branch summary, and commits in `docs/task/`.

---

## 🚀 SESSION START (/gov-context)

1.  **Read Worldview**: Read `docs/project/metadata.yaml` and `docs/project/context.md`.
2.  **Activate Skill**: Call `activate_skill(name="task-context")` to reconstruct the task state.
3.  **Greet**: *"GCC Context loaded. Tier 1 (Project) & Tier 2 (Task) synchronized. Ready."*

---

## 🛑 SESSION END (/gov-writeback)

1.  **Knowledge Extraction**: Did you learn something universal (e.g., a bug pattern or new dependency)?
    - **IF YES**: Update `docs/project/context.md` (Lessons Learned) or `metadata.yaml`.
2.  **Checkpointing**:
    - If a milestone was reached: Call `activate_skill(name="task-commit")`.
    - If partial progress: Update `summary.md` (Current State / Next Action) directly.
3.  **Hermetic Check**: Ensure all references in your write-back are internal to `.ai-governance/`.

---

## ❌ Constraints
- Do not append to a single log file. Use the GCC tree.
- Do not create "knowledge debt" by leaving evidence in external `/tmp` or `artifacts/` folders.
