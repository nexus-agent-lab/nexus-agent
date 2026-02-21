# Implementation Plan: Local Testing Automation

## Goal
Establish a fast, local feedback loop for developers using `ruff` for linting and `pytest` for testing, without bloating the production Docker image.

## Proposed Changes

### 1. Dependency Management
- **[MODIFY] [requirements.txt](file:///Users/michael/work/nexus-agent/requirements.txt)**: Remove `ruff` and `pytest`.
- **[NEW] [requirements-dev.txt](file:///Users/michael/work/nexus-agent/requirements-dev.txt)**: Dedicated file for local dev tools.

### 2. Automation Scripts
- **[NEW] [check.sh](file:///Users/michael/work/nexus-agent/scripts/check.sh)**: A unified script to run `ruff check --fix` and `pytest`.
- **[NEW] [pre-commit](file:///Users/michael/work/nexus-agent/.git/hooks/pre-commit)**: A Git hook to automatically trigger `check.sh` before every commit.

### 3. Configuration
- **[MODIFY] [pyproject.toml](file:///Users/michael/work/nexus-agent/pyproject.toml)**: Ensure Ruff and Pytest are configured for the local environment.

## Verification Plan
1. **Manual Execution**: Run `./scripts/check.sh` and confirm it passes.
2. **Hook Execution**: Attempt a dummy commit and verify the checks run automatically.
