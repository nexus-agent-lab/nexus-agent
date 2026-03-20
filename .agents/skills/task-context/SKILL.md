---
name: task-context
description: Load and synthesize the current GCC state (v2.1).
---

# task-context Skill

## Purpose
Reconstruct the project and task state by reading the GCC tree. Must be run at the start of every session.

## Instructions

1. **Safety Check**:
   - Verify `.ai-governance/docs/project/metadata.yaml` exists. Read it to understand the `repo_structure` and `execution_context` (commands).
   - If not found, warn the user.

2. **Core Context**:
   - Read `.ai-governance/docs/task/active/task.md` (Objective).
   - Read `.ai-governance/docs/task/active/verification.md` (Success status).

3. **Active Branch State**:
   - Identify the active branch (default: `main`).
   - Read `branches/<branch>/summary.md`. **Verify it contains: Branch Intent, Current State, Known Risks, Next Action.**
   - Read the 2 most recent commits in `branches/<branch>/commits/`. **Focus on Decisions and Next Steps.**

4. **Output Structured View**:
   ```text
   ## GCC v2.1 CONTEXT VIEW
   - **Env**: [Runtime from metadata]
   - **Commands**: [Run/Test cmds from metadata]
   - **Goal**: [Objective from task.md]
   - **State**: [Current State from summary.md]
   - **Recent Decisions**: [Key notes from latest commits]
   - **Next Action**: [From summary.md]
   ```

5. **Ask**: *"Shall I proceed with [Next Action] or do you have a different direction?"*
