# /ctx-load
Restore repo working context from project-context files.

Read:
- `.project-context/docs/project/metadata.yaml`
- `.project-context/docs/task/active/index.md`
- `.project-context/docs/task/active/task.md`
- `.project-context/docs/task/active/summary.md`

If `summary.md` is missing, use a fallback compatibility file if present.

Output:
- Current Task Goal
- Completed Progress
- Current Risks
- Next Action

Constraints:
- No code changes
- No file edits
- Keep it short
- Wait for user confirmation before implementation
