---
name: task-bootstrap
description: Initialize the refined GCC structure (v2.1).
---

# task-bootstrap Skill

## Purpose
Initialize a new active task tree using the refined GCC v2.1 schema.

## Instructions

1. **Check Metadata**: Ensure `.ai-governance/docs/project/metadata.yaml` exists. If not, draft one based on the current repo structure and ask the user to verify.

2. **Create Tree**:
   - `.ai-governance/docs/task/active/`
   - `.ai-governance/docs/task/active/task.md`
   - `.ai-governance/docs/task/active/verification.md`
   - `.ai-governance/docs/task/active/branches/main/commits/`
   - `.ai-governance/docs/task/active/branches/main/summary.md`

3. **Initialize Summary**: Ensure `summary.md` has the mandatory sections:
   - Branch Intent
   - Current State: "Initialized"
   - Known Risks: "None"
   - Next Action: "Drafting implementation plan"

4. **Ask for Objective**: Prompt the user for the `task.md` contents.
