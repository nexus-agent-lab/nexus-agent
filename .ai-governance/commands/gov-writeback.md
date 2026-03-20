---
name: gov-writeback
description: Write back the current execution state before ending the session.
---

# /gov-writeback

Purpose:
Write back the current execution state before ending the session so the next agent can resume quickly.

## Update logic

1.  **Extract Knowledge**: If you learned universal project patterns, update `.ai-governance/docs/project/context.md`.
2.  **Capture Assets**: If you have critical logs/artifacts, move them to `.ai-governance/docs/task/active/assets/`.
3.  **Finalize State**:
    - Milestone reached? -> Call `activate_skill(name="task-commit")`.
    - Partial progress? -> Overwrite `.ai-governance/docs/task/active/summary.md`.

## Rules

- **Hermeticity**: Ensure all references are internal to `.ai-governance/`.
- Overwrite the file; do not append logs.
