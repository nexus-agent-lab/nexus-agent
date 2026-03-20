Before ending the session, write back the resumable task state.

Overwrite:
`.project-context/docs/task/active/summary.md`

Use:

# Active Task Summary

## Current State
<what is done and current implementation status>

## What Changed Recently
<recent meaningful changes>

## Known Risks / Blockers
<blockers, unresolved issues, fragile assumptions, missing checks>

## Next Action
<single concrete next step>

Rules:
- overwrite instead of append
- concise and practical
- optimize for fast resume by another agent
- clearly mark uncertainty
