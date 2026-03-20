---
name: gov-writeback
description: Write back the current execution state before ending the session.
---

# /gov-writeback

Purpose:
Write back the current execution state before ending the session so the next agent can resume quickly.

## Update target

Write or overwrite:
- `.ai-governance/docs/task/active/summary.md`

## Source inputs

Use:
- current repository state
- work completed in this session
- current known blockers
- the most useful immediate next step

## Required template

Write `summary.md` using exactly this structure:

# Summary

## Branch Intent
<current task or current phase goal>

## Current State
<what has been completed and the current state of implementation>

## Known Risks
<open issues, blockers, fragile assumptions, missing validation>

## Next Action
<the next concrete step the next agent should take>

## Rules

- **Gemini CLI**: Call `activate_skill(name="task-commit")` if a milestone was reached.
- Overwrite the file; do not append logs.
- Keep it concise.
- Prefer concrete implementation state over narrative.
- Include only information useful for the next agent to resume work.
- Do not create fake certainty.
- If something is incomplete or unverified, say so clearly.
