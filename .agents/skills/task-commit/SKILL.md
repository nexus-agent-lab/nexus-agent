---
name: task-commit
description: Create a structured cognitive checkpoint (v2.1).
---

# task-commit Skill

## Purpose
Serialize current progress, reasoning, and decisions into the GCC history. Use this when a meaningful milestone is achieved.

## Instructions

1. **Verify Mandatory Fields**: Your commit MUST include:
   - **Intent**: What did you set out to solve?
   - **Previous Context**: What state did you start from?
   - **Changes Made**: Specific files and logic changes.
   - **Decisions**: **WHY** did you choose this path? (Critical for cross-agent alignment).
   - **Verification**: Evidence (test output, logs).

2. **Generate Commit**:
   - Create `branches/<branch>/commits/YYYY-MM-DD-HHMM-[slug].md`.

3. **Update Summary**:
   - Update `branches/<branch>/summary.md`. 
   - Refresh the `Current State`, append the new commit to `Latest Commits`, and update the `Next Action`.

4. **Final Check**: Ensure you didn't just summarize code; summarize the **cognitive decisions** that influenced the code.
