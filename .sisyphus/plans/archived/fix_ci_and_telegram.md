# Work Plan: Fix CI (GitHub Actions) and Telegram Conflict Guidance

## Objective
1. Fix GitHub Actions failures by aligning the CI environment with the real requirements (Postgres + pgvector).
2. Ensure tests that require a real database are properly handled in CI.
3. Provide guidance on resolving Telegram Conflict.

## Implementation Steps

### Task 1: Update GitHub Actions Workflow
**File**: `.github/workflows/ci.yml`
**Actions**:
- Add a `postgres` service container using `ankane/pgvector:latest`.
- Configure environment variables for the test database.
- Standardize the `Ruff` and `Pytest` execution steps.

### Task 2: Fix Telegram Conflict (Operational)
- Add a check/note in `app/interfaces/telegram.py` to log a clearer message when Conflict occurs.
- Advise user to use separate tokens for Dev and Prod.

### Task 3: Quality Assurance
- Run `bash scripts/dev_check.sh` locally one last time.
- Push the CI change to trigger a remote run.

## Final Verification
- [ ] GitHub Actions badge turns green.
- [ ] No more IndentationErrors in core logic.
