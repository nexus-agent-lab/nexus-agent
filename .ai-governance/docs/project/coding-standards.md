# Coding Standards

## General Principles
- **KISS**: Keep It Simple, Stupid.
- **DRY**: Don't Repeat Yourself.
- **Small Commits**: One logical change per commit.
- **Minimal Changes**: Avoid refactoring unrelated code unless necessary.

## Style Guidelines
- [Language-specific style guide, e.g., PEP 8 for Python]
- No commented-out code.
- Descriptive variable and function names.

## Testing Requirements
- Every new feature must have corresponding unit tests.
- Bug fixes must include a regression test.
- Aim for >[80]% coverage on core logic.

## Documentation Requirements
- Update `README.md` if public APIs or installation steps change.
- Keep `docs/project/architecture.md` current with major changes.

## Git Hygiene
- Branch naming: `(feat|bug|task)/T-<id>-description`
- Commit messages: `[T-<id>] action: description`
