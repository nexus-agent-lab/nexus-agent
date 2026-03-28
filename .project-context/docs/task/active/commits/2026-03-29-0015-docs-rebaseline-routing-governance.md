# Checkpoint

## Intent
Rebaseline the active project context and architecture docs so the next implementation phase is driven by unified routing, governance, scope, and metadata convergence rather than by stale per-feature TODOs.

## Previous Context
- Browser MCP transport, Plan A stabilization, routing anchors + pgvector, admin/auth cleanup, WeChat Phase 1, and model capability catalog work had already been implemented.
- The active project-context queue still listed multiple already-completed items as if they were current next steps.
- The user explicitly called out that abstraction debt still exists, especially around Home Assistant and other MCP integrations remaining partially hardcoded.

## Changes Made
- Updated [index.md](/Users/michael/work/nexus-agent/.project-context/docs/task/active/index.md):
  - re-centered the active goal around routing/governance/scope unification
  - removed completed work from the active next-step queue
  - replaced the old mixed TODO list with a 4-part priority queue:
    - unified modeling
    - runtime prefilter integration
    - hardcoded-path reduction
    - live scenario validation
- Updated [summary.md](/Users/michael/work/nexus-agent/.project-context/docs/task/active/summary.md):
  - reflected that the highest-priority gap is now abstraction quality, not missing capability
  - updated the short next action statement to match the new control-plane direction
- Added [routing_governance_scope_unification.md](/Users/michael/work/nexus-agent/docs/architecture/routing_governance_scope_unification.md) as the new umbrella architecture note covering:
  - routing tree
  - scope/group/policy prefilter
  - unified metadata contract
  - governance tiers
  - session/identity model
  - integration-specific hardcoding debt
- Updated subsystem docs to reflect current status and next-phase consolidation:
  - [skill_routing_anchor_recall_with_local_vector_db.md](/Users/michael/work/nexus-agent/docs/architecture/skill_routing_anchor_recall_with_local_vector_db.md)
  - [mcp_session_isolation_and_browser_evolution.md](/Users/michael/work/nexus-agent/docs/architecture/mcp_session_isolation_and_browser_evolution.md)
  - [langgraph_skill_worker_migration.md](/Users/michael/work/nexus-agent/docs/architecture/langgraph_skill_worker_migration.md)
  - [user_groups_abac.md](/Users/michael/work/nexus-agent/docs/architecture/user_groups_abac.md)

## Decisions
- Treated browser, Home Assistant, and other MCP integrations as examples inside one future control-plane model rather than as separate roadmap branches.
- Explicitly recorded hardcoding debt as a platform convergence problem, not a bug list.
- Kept completed work in background/context sections but removed it from the active next-step queue so future agents are not misled.

## Verification
- This checkpoint is documentation-only.
- Verified by reading the affected project-context and architecture docs after editing to ensure:
  - completed work is no longer listed as active next-step work
  - the new unified direction is recorded in both active context and architecture docs
