---
name: ctx-load
description: Restore the current working context for a new agent session.
---

# /ctx-load

Purpose:
Restore the current working context for a new agent session from repo-native project-context files.

## Read in order

1. `.project-context/docs/project/metadata.yaml`
2. `.project-context/docs/task/active/index.md`
3. `.project-context/docs/task/active/task.md`
4. `.project-context/docs/task/active/summary.md`
5. If `summary.md` does not exist, fall back to any available compatibility file in the same folder.

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

- **Gemini CLI**: Call `activate_skill(name="context-load")` after reading these files to synthesize state.
- Do not modify code.
- Do not modify project-context files.
- Do not infer extra requirements unless strongly supported by the files.
- Prefer `summary.md` as the source of truth for current state.
- Keep output brief and execution-oriented.
- If files are missing, explicitly say what is missing.
- After outputting the context, stop and wait for user confirmation.
