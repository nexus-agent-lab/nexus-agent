---
name: task-merge
description: Consolidate exploration findings back into the main GCC context (v2.1).
---

# task-merge Skill

## Purpose
Summarize the successful outcomes of an exploration branch and integrate them into the `main` reasoning chain.

## Instructions

1. **Summarize Source Branch**:
   - Read `branches/<source>/summary.md` and the final commits.
2. **Create Merge Commit on Main**:
   - Run `task-commit` logic targeting `branches/main/commits/`.
   - **Intent**: Merge branch `<source>`.
   - **Decisions**: Summarize WHY the findings of `<source>` were accepted and what was learned.
3. **Update Main Summary**:
   - Refresh `Current State` on `main` to reflect the newly integrated functionality.
   - Update `Next Action`.
4. **Cleanup**: Ask the user if the `<source>` directory should be deleted or kept as an archived reference.
