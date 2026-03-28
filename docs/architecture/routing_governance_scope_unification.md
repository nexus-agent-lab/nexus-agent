# Routing, Governance, and Scope Unification

## 1. Goal

Define the next control-plane architecture for Nexus so routing, permissioning, scope, and integration governance are handled by one coherent model rather than by scattered integration-specific logic.

The platform objective is no longer just:

- connect a tool
- register a skill
- make a query work once

The objective is:

**tools, skills, and MCP integrations should be classified, governed, filtered, and injected through one shared control-plane contract.**

## 2. Why This Is The Current Priority

Recent implementation work has already landed the following foundations:

- browser MCP transport repair and real Playwright tool registration
- skill routing anchors backed by Postgres + pgvector
- Plan A stabilization for large browser outputs, 429 backoff, token-aware compacting, and session-scoped inspector workspaces
- ABAC group filtering at the existing permission check layer
- better worker-aware tool shaping and metadata-driven routing than the previous hardcoded graph paths

The remaining architecture gap is not "another feature is missing." It is that:

- routing still does not fully pre-shape the search space by domain and scope
- permission checks still happen too late in some paths
- browser, Home Assistant, and other integrations still carry code-level assumptions
- MCP/local/static tool metadata is not yet one fully normalized contract

This is now the highest-value platform work because it affects:

- routing quality
- token efficiency
- multi-user safety
- integration onboarding
- future per-user MCP session support

## 3. Unified Runtime Pipeline

The target runtime order should be:

1. `domain/context pre-gate`
2. `scope/group/policy prefilter`
3. `anchor recall`
4. `skill aggregation`
5. `worker-aware toolbelt shaping`
6. `call-time enforcement`

### 3.1 Domain / Context Pre-Gate

Before vector recall, classify the request into one or more candidate domains or contexts such as:

- `home`
- `web`
- `system`
- `memory`
- `communication`
- `code`

This stage should shrink the candidate search space before skill recall and tool injection.

### 3.2 Scope / Group / Policy Prefilter

Before building the final toolbelt, exclude tools/skills that are not available in the current execution context.

Examples:

- user lacks required group
- tool requires a user/session scope that is not present
- integration is disabled for this deployment
- tool group is outside the allowed policy tier

This stage should happen before final tool injection, not only at tool call time.

### 3.3 Anchor Recall And Skill Aggregation

After the search space is reduced, use routing anchors to recall candidate skills and aggregate anchor hits back to skills.

This should remain compatible with current:

- `routing_examples`
- skill routing anchors in pgvector
- worker-aware tool shaping

### 3.4 Worker-Aware Toolbelt Shaping

Once domain, policy, and recalled skill candidates are known, build the smallest toolbelt needed by the current worker path.

This keeps the current migration direction:

- routing and policy decide availability
- worker shaping decides execution narrowness

### 3.5 Call-Time Enforcement

Call-time permission checks still remain necessary for final safety, but they should be the last guard, not the first time policy is applied.

## 4. Unified Metadata Contract

The next implementation phase should normalize metadata across four layers:

```text
plugin
  -> tool_group
    -> tool
skill
```

### 4.1 Plugin-Level Metadata

Plugin metadata should answer:

- what trust/governance tier this integration belongs to
- what deployment-level scope rules exist
- whether the integration is public, shared, or identity-bearing

Suggested fields:

- `integration_tier`
- `allowed_groups`
- `required_role`
- `identity_mode`
- `session_policy`

### 4.2 Tool Group Metadata

Tool groups are required for mixed-risk MCP integrations such as Playwright.

Suggested fields:

- `tool_group`
- `scope`
- `risk_level`
- `side_effect`
- `audit_level`
- `identity_mode`
- `session_policy`

### 4.3 Tool Metadata

All tools should converge on:

- `capability_domain`
- `operation_kind`
- `scope`
- `risk_level`
- `side_effect`
- `allowed_groups`
- `required_role`
- `identity_mode`
- `session_policy`
- `preferred_worker`

### 4.4 Skill Metadata

Skills should converge on:

- `routing_domains`
- `routing_examples`
- `routing_weight`
- `required_tools`
- optional policy hints used only to narrow routing, not to override runtime enforcement

## 5. Governance Tiers

Integrations should be governed at least in these buckets:

### 5.1 System-Critical

Examples:

- Home Assistant
- filesystem-like private data integrations
- browser integrations once they become authenticated or stateful

Properties:

- higher review bar
- stronger metadata requirements
- explicit scope/session policy required

### 5.2 Trusted Internal

Examples:

- internally maintained MCPs
- company/home deployment specific integrations

Properties:

- may use deployment-shared credentials
- still require clear metadata contract

### 5.3 Community

Examples:

- generic public MCP tools
- low-trust external integrations

Properties:

- restricted by default
- should not gain broad access unless explicitly elevated

## 6. Session / Identity Model

The control plane should treat session and identity as first-class metadata, not as integration-specific special cases.

Supported scope targets should become:

- `public`
- `deployment`
- `group`
- `user`
- `session`

Supported identity modes should become:

- `none`
- `deployment_credential`
- `user_credential`
- `nexus_managed_session`

This allows:

- current browser Phase A to remain `public`
- future authenticated browser to become `user` + `session`
- Home Assistant to stay deployment-shared while still respecting ABAC
- future user-scoped MCP integrations to be modeled without new core exceptions

## 7. Integration-Specific Hardcoding Debt

The current codebase still carries several architecture debts that should now be treated explicitly as convergence work:

- Home Assistant reliability still includes runtime guardrails and assumptions in code rather than purely metadata-driven policy
- browser tool grouping is documented but not yet enforced as first-class `tool_group` policy
- MCP metadata coverage is still incomplete across all registered tools
- tool catalog and worker filtering still act partly as a migration-phase compatibility layer
- the system is not yet at the point where a new MCP/skill naturally plugs in without touching core assumptions

This debt should be treated as a platform refactor target, not as a sign that the current integrations are failures.

The important direction is:

**future work should converge abstractions, not keep adding special-case patches for one integration at a time.**

## 8. Acceptance / Validation Targets

The next implementation phase should be validated against a small, concrete set of runtime expectations:

- browser research queries should hit `web_browsing`
- home control queries should hit `homeassistant`
- ambiguous requests such as `查日志` should not drift into browser or Home Assistant
- tools outside user scope should not enter the final toolbelt
- session-scoped integrations should not appear available when no session exists
- integration onboarding should become more metadata-driven and less hardcoded

## 9. Relationship To Existing Docs

This document becomes the control-plane umbrella over:

- `skill_routing_anchor_recall_with_local_vector_db.md`
- `mcp_session_isolation_and_browser_evolution.md`
- `langgraph_skill_worker_migration.md`
- `user_groups_abac.md`

Those documents remain valid, but should now be read as subsystem slices inside this broader unification effort.
