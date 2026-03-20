---
name: gov-context
description: Restore the current working context for a new agent session.
---

# /gov-context

Purpose:
Restore the current working context for a new agent session from repo-native governance files.

## Read in order

1. `.ai-governance/docs/task/active/task.md`
2. `.ai-governance/docs/task/active/summary.md`
3. If `summary.md` does not exist, fall back to any available handoff-style file (e.g., `handoff.md`) in the same folder.

## Output format

Return a concise structured handoff using exactly these sections:

### Current Task Goal
What the current task is trying to achieve.

### Completed Progress
What is already done and should not be repeated.

### Current Risks
Open questions, blockers, assumptions, or fragile areas.

### Next Action
The single most important next step to take.

## Rules

- **Gemini CLI**: Call `activate_skill(name="task-context")` after reading these files to synthesize state.
- Do not modify code.
- Do not modify governance files.
- Do not infer extra requirements unless strongly supported by the files.
- Prefer `summary.md` as the source of truth for current state.
- Keep output brief and execution-oriented.
- If files are missing, explicitly say what is missing.
- After outputting the context, stop and wait for user confirmation.
