---
name: context-load
description: Load and synthesize the current Project Context state (v3.2).
---

# context-load Skill

## Purpose
Reconstruct the project and task state by reading the Project Context tree. Must be run at the start of every session.

## Instructions

1. **Safety Check**:
   - Verify `.project-context/docs/project/metadata.yaml` exists. Read it to understand the `repo_structure` and `execution_context` (commands).
   - If not found, warn the user.

2. **Core Context**:
   - Read `.project-context/docs/task/active/index.md` first.
   - Read `.project-context/docs/task/active/task.md` if it exists.
   - Read `.project-context/docs/task/active/summary.md` if it exists.
   - Read `.project-context/docs/task/active/verification.md` if it exists.

3. **Compatibility Fallback**:
   - If `index.md` or `summary.md` are missing, look for a legacy branch-based summary under `.project-context/docs/task/active/branches/main/summary.md`, or in older repos under `.ai-governance/docs/task/active/branches/main/summary.md`.
   - Treat any branch-based summary as compatibility input, not the preferred source of truth.

4. **Milestone Context**:
   - Read the 2 most recent commits in `.project-context/docs/task/active/commits/` if present.
   - If the user explicitly names a workstream, optionally read `.project-context/docs/task/active/workstreams/<name>/summary.md` and its recent commits.

5. **Output Structured View**:
   ```text
   ## PROJECT CONTEXT v3.2 VIEW
   - **Env**: [Runtime from metadata]
   - **Commands**: [Run/Test cmds from metadata]
   - **Goal**: [Objective from task.md]
   - **State**: [Current State from index.md or summary.md]
   - **Recent Decisions**: [Key notes from latest commits]
   - **Next Action**: [From index.md or summary.md]
   ```

6. **Ask**: *"Shall I proceed with [Next Action] or do you have a different direction?"*
