# AI Agent Instructions

<!-- BEGIN AI-GOVERNANCE -->
## Project Context Layer (v3.2)
This repository uses a Project Context shared context layer.

**Rules**: `.project-context/AGENTS.shared.md` | **Contract**: `.project-context/repo-contract.md`

### Required Every Session
**START**: Run `/ctx-load` to load current task state and objective.
**END**: Run `/ctx-save` to leave a resumable summary for the next agent.

Default mode uses a single active task in `.project-context/docs/task/active/`. Optional workstreams are advanced mode only.
<!-- END AI-GOVERNANCE -->
