# Verification Runbook

## Verification Hierarchy
Before declaring a task finished, follow these steps in order:

1. **Linting & Type Checking**: Ensure static analysis passes.
2. **Unit Tests**: Run localized tests for the changed code.
3. **Integration Tests**: Verify components work together.
4. **Build Verification**: Ensure the production build succeeds.
5. **Manual Check**: Perform a manual walkthrough of the changed UI/API.

## Recording Results
Log all results in `docs/task/<ticket-id>/verification.md` using the following format:

| Step | Method | Result | Logs/Notes |
|------|--------|--------|------------|
| Lint | `npm run lint` | OK | No errors |
| Test | `npm test` | OK | 14/14 passed |

## Minimum Standard
- All tests MUST pass.
- No new lint warnings.
- If verification is skipped (e.g., minor typo), justify it in the verification log.
