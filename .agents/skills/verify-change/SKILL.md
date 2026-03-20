---
name: verify-change
description: Validate changes and record evidence in the GCC tree (v2.1).
---

# verify-change Skill

## Purpose
This skill is used to execute test suites and record their output in the canonical `verification.md` or a `commit`.

## Instructions

1. **Read Metadata**: Check `.ai-governance/docs/project/metadata.yaml` for the `test_cmd`.
2. **Execute Tests**: Run the command. Capture the output.
3. **Record Evidence**:
   - Append a timestamped entry to `.ai-governance/docs/task/active/verification.md`.
   - Or, include the output in the `Verification` block of your next `task-commit`.
4. **Status**: Report to the user whether the validation was successful or identifying failures.
