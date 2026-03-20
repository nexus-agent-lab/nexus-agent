# /gov-context
Read the repo governance context and prepare a handoff summary.

Steps:
1. Read `.ai-governance/docs/task/active/task.md`
2. Read `.ai-governance/docs/task/active/summary.md`
3. If `summary.md` is missing, use any fallback handoff file in the same folder.

Then reply with exactly these sections:

## Current Task Goal
## Completed Progress
## Current Risks
## Next Action

Rules:
- Do not edit any files
- Do not change code
- Keep the summary brief and practical
- Prefer `summary.md` as the current source of truth
- Stop after summarizing and wait for confirmation
