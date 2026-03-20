---
name: context-checkpoint
description: Create a structured project-context checkpoint (v3.2).
---

# context-checkpoint Skill

## Purpose
Serialize current progress, reasoning, and decisions into the Project Context history. Use this when a meaningful milestone is achieved.

## Instructions

1. **Verify Mandatory Fields**: Your checkpoint MUST include:
   - **Intent**: What did you set out to solve?
   - **Previous Context**: What state did you start from?
   - **Changes Made**: Specific files and logic changes.
   - **Decisions**: Why this path was chosen.
   - **Verification**: Evidence such as test output or logs.

2. **Generate Checkpoint**:
   - Default target: `docs/task/active/commits/YYYY-MM-DD-HHMM-[slug].md`.
   - Optional advanced target: `docs/task/active/workstreams/<name>/commits/YYYY-MM-DD-HHMM-[slug].md`.

3. **Update Summary**:
   - Update `docs/task/active/summary.md` by default.
   - Refresh `docs/task/active/index.md` with the latest milestone and next step.
   - If operating inside a named workstream, update that workstream summary as well.

4. **Final Check**: Summarize the cognitive decisions that influenced the code, not just the code itself.
