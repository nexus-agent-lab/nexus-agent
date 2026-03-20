---
name: ctx-load
description: Restore the current working context for a new agent session.
---

# /ctx-load

Purpose:
Restore the current working context for a new agent session from repo-native project-context files.

## Read in order

1. `.project-context/docs/project/metadata.yaml` (Env & Commands)
2. `.project-context/docs/project/context.md` (Architecture & History)
3. `.project-context/docs/task/active/index.md` (Fast status view)

## Expand only if needed

4. `.project-context/docs/task/active/task.md` (Goal)
5. `.project-context/docs/task/active/summary.md` (Progress)
6. `.project-context/docs/task/active/verification.md` (Latest validation state)

## Rules

- **Gemini CLI / Antigravity**: Call `activate_skill(name="context-load")` after reading these files to synthesize the session brief.
- Prefer `index.md` and `summary.md` as the single active-task source of truth.
- If files are missing, offer to run `activate_skill(name="context-bootstrap")`.
- Keep output brief and execution-oriented.
