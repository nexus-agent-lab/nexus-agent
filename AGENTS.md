# AI Agent Instructions

<!-- BEGIN AI-GOVERNANCE -->
## Project Context Layer (v3.2)
This repository uses a Project Context shared context layer.

**Rules**: `.project-context/AGENTS.shared.md` | **Contract**: `.project-context/repo-contract.md`

### Required Every Session
**START**: Invoke the project-context agent command `ctx-load` to load current task state and objective. Do not execute it in bash.
**END**: Invoke the project-context agent command `ctx-save` to leave a resumable summary for the next agent. Do not execute it in bash.

Default mode uses a single active task in `.project-context/docs/task/active/`. Optional workstreams are advanced mode only.
<!-- END AI-GOVERNANCE -->
