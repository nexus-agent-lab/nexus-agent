---
name: gov-context
description: Restore the current working context for a new agent session.
---

# /gov-context

Purpose:
Restore the current working context for a new agent session from repo-native governance files.

## Read in order

1. `.ai-governance/docs/project/metadata.yaml` (Env & Commands)
2. `.ai-governance/docs/project/context.md` (Architecture & History)
3. `.ai-governance/docs/task/active/task.md` (Goal)
4. `.ai-governance/docs/task/active/summary.md` (Progress)

## Rules

- **Gemini CLI / Antigravity**: Call `activate_skill(name="task-context")` after reading these files to synthesize the session brief.
- If files are missing, offer to run `activate_skill(name="task-bootstrap")`.
- Keep output brief and execution-oriented.
