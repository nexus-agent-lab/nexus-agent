# /ctx-save
Write back the current working state for the next agent.

Target file:
`.project-context/docs/task/active/summary.md`

Overwrite the file using this template:

# Active Task Summary

## Current State
<completed work and current implementation status>

## What Changed Recently
<recent meaningful changes>

## Known Risks / Blockers
<blockers, unresolved issues, weak assumptions, missing checks>

## Next Action
<single most important next step>

Rules:
- Overwrite instead of append
- Keep it concise and recovery-oriented
- Only include information useful for resuming work
- Be explicit about uncertainty or incomplete validation
