---
name: ctx-save
description: Write back the current execution state before ending the session.
---

# /ctx-save

Purpose:
Write back the current execution state before ending the session so the next agent can resume quickly.

## Update logic

1. **Extract Knowledge**: If you learned universal project patterns, update `.project-context/docs/project/context.md`.
2. **Capture Assets**: If you have critical logs or artifacts, move them to `.project-context/docs/task/active/assets/`.
3. **Refresh Fast Index**: Update `.project-context/docs/task/active/index.md` with the current goal, status, next step, latest verification, and latest milestone.
4. **Finalize State**:
   - Default path -> Overwrite `.project-context/docs/task/active/summary.md`.
   - Milestone reached? -> Call `activate_skill(name="context-checkpoint")`.

## Rules

- **Hermeticity**: Ensure all references are internal to `.project-context/`.
- Overwrite the file; do not append logs.
