---
name: context-bootstrap
description: Initialize the Project Context structure (v3.2).
---

# context-bootstrap Skill

## Purpose
Initialize a new active task tree using the Project Context v3.2 schema.

## Instructions

1. **Check Metadata**: Ensure `.project-context/docs/project/metadata.yaml` exists. If not, draft one based on the current repo structure and ask the user to verify.

2. **Create Tree**:
   - `.project-context/docs/task/active/`
   - `.project-context/docs/task/active/index.md`
   - `.project-context/docs/task/active/task.md`
   - `.project-context/docs/task/active/summary.md`
   - `.project-context/docs/task/active/verification.md`
   - `.project-context/docs/task/active/commits/`
   - `.project-context/docs/task/active/workstreams/`

3. **Initialize Summary**: Ensure `summary.md` has:
   - Current State: "Initialized"
   - Known Risks: "None"
   - Next Action: "Drafting implementation plan"

4. **Initialize Index**: Ensure `index.md` contains:
   - Current Goal
   - Current Status: "Initialized"
   - Next Step: "Drafting implementation plan"
   - Latest Verification: "Not run yet"
   - Latest Milestone: "None yet"

5. **Compatibility Note**: Older `branches/main/summary.md` structures may still exist in previously installed repos, but do not create them in new installs.

6. **Ask for Objective**: Prompt the user for the `task.md` contents.
