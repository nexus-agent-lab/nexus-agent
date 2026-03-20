---
name: task-branch
description: Fork the GCC reasoning tree into an isolated exploration path (v2.1).
---

# task-branch Skill

## Purpose
Isolate an experimental context within the active task to avoid polluting the `main` branch with failed reasoning or hypothesis tests.

## Instructions

1. **Ask for Branch Name**: e.g., `experiment-db-v2`.
2. **Create Tree**: `.ai-governance/docs/task/active/branches/<name>/commits/`.
3. **Initialize Summary**:
   - Copy `branches/main/summary.md` to `branches/<name>/summary.md`.
   - Update `Branch Intent`: "Exploring [specific hypothesis]".
   - Update `Current State`: "Forked from main at [commit ID]".
   - Update `Next Action`: "Validating first prototype".
4. **Confirm**: *"Switched focused to GCC branch `<name>`. Commits will be isolated here until you run `task-merge`."*
