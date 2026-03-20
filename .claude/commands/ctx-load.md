# /ctx-load
Read the project context and prepare a handoff summary.

Steps:
1. Read `.project-context/docs/project/metadata.yaml`
2. Read `.project-context/docs/task/active/index.md`
3. Read `.project-context/docs/task/active/task.md`
4. Read `.project-context/docs/task/active/summary.md`
5. If `summary.md` is missing, use any fallback compatibility file in the same folder.

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
