# AI Agent Instructions

<!-- BEGIN AI-GOVERNANCE -->
## Shared Governance Layer (GCC Model v2.1)
This repository uses a Git-Context-Controller (GCC) shared governance layer.

**Rules**: `.ai-governance/AGENTS.shared.md` | **Contract**: `.ai-governance/repo-contract.md`

### Required Every Session
**START**: Run `/gov-context` to load current task state and objective.
**END**: Run `/gov-writeback` to leave a resumable summary for the next agent.

GCC records context/decisions in `.ai-governance/docs/`. Do not treat IDE memory or chat history as durable state.
<!-- END AI-GOVERNANCE -->
