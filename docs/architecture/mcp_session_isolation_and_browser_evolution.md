# MCP Session Isolation And Browser Evolution

## 1. Goal

Define the correct architecture for browser access and future authenticated MCP integrations in a multi-user Nexus deployment.

The main decision is:

**Playwright browser access should start as a built-in, public, stateless, read-only plugin, then evolve into a generic Nexus-managed per-user MCP session model.**

This should not be treated as a Playwright-only special case.

The same architectural problem will recur for future MCP integrations such as:

- browser login state
- Lark / Feishu user identity
- GitHub personal access
- Google workspace access
- any MCP integration where multiple Nexus users need isolated identities, sessions, or credentials

So the design target is a reusable Nexus-side session isolation layer for MCP plugins.

## 2. Why This Matters

The current Web Browser plugin is now technically connected and usable through Playwright MCP.

That solves transport and tool registration, but it does not yet solve:

- multi-user login isolation
- authenticated browsing
- safe session reuse
- browser-side side effects under different user identities

Playwright exposes a mixed-risk tool surface:

- low-risk public reads such as navigation and snapshots
- interaction tools such as click and type
- higher-risk tools such as form filling, file upload, and browser-side code execution

The current Nexus permission model is too coarse for this type of MCP integration.

## 3. Current State

### 3.1 What Works

The current browser integration supports:

- MCP connection over `/mcp`
- Playwright tool registration into the Nexus toolset
- public browsing, snapshots, and screenshots

This is already useful for:

- public website reading
- screenshot/snapshot evidence gathering
- lightweight search-like browsing

### 3.2 Current Risk

The current architecture should **not** yet be treated as safe for multi-user authenticated browsing.

Without explicit Nexus-side session isolation, these risks exist:

- one user's login state may be reused by another user
- cookies or storage state may leak across users
- tabs or browser contexts may be shared unintentionally
- snapshots or screenshots may expose another user's authenticated page state

So the near-term rule should be strict:

**Until Nexus explicitly manages per-user MCP session scope, browser access must remain public, stateless, and read-only.**

## 4. Product Decision

Browser support should evolve in two phases.

### Phase A: Public Stateless Browser

This is the immediate operating mode.

Properties:

- public pages only
- no login persistence
- no per-user browser state
- no shared authenticated session
- read-only usage by default

Allowed use cases:

- reading public pages
- taking screenshots of public pages
- summarizing public content from snapshots

Disallowed or deferred use cases:

- using saved login state
- filling forms as a logged-in user
- uploading files in authenticated sessions
- reusing browser identity between users

### Phase B: Nexus-Managed Per-User MCP Sessions

This is the long-term architecture.

Properties:

- Nexus user identity maps to isolated MCP-side session state
- each user gets a separate authenticated browser/session context
- credentials and state are managed by Nexus, not implicitly by the MCP service
- audit trails tie browser actions to the actual Nexus principal and session scope

This phase should be implemented as a general MCP session model, not a Playwright-only mechanism.

## 5. Browser Tool Grouping

Before introducing authenticated sessions, Playwright should be split into permission groups.

### 5.1 `browser_read`

Low-risk, public-read capabilities.

Suggested tools:

- `browser_navigate`
- `browser_navigate_back`
- `browser_snapshot`
- `browser_take_screenshot`
- `browser_wait_for`
- `browser_tabs`
- `browser_console_messages`
- `browser_network_requests`
- `browser_resize`
- `browser_close`

Default policy:

- allowed in the first phase
- no authenticated state assumed

### 5.2 `browser_interact`

Medium-risk interaction tools.

Suggested tools:

- `browser_click`
- `browser_hover`
- `browser_press_key`
- `browser_type`
- `browser_select_option`
- `browser_drag`
- `browser_handle_dialog`

Default policy:

- disabled for the first public-read phase
- later allowed only with explicit policy and isolated sessions

### 5.3 `browser_sensitive`

High-risk tools that can submit data, execute code, or act inside authenticated sessions.

Suggested tools:

- `browser_fill_form`
- `browser_file_upload`
- `browser_evaluate`
- `browser_run_code`

Default policy:

- disabled in the first phase
- require stronger role/group policy
- require isolated authenticated session support

### 5.4 `browser_runtime`

Operational/runtime tools rather than normal user browsing actions.

Suggested tools:

- `browser_install`

Default policy:

- admin-only or internal-only

## 6. Why Plugin-Level RBAC Is Not Enough

The current plugin model supports:

- `required_role`
- `allowed_groups`

at the plugin level.

That is useful, but not enough for Playwright-like MCP servers because one plugin contains tools with very different risk profiles.

For example:

- `browser_snapshot` is a read capability
- `browser_click` is an interaction capability
- `browser_run_code` is effectively arbitrary code execution inside a browser context

These should not share one flat permission class.

So Nexus needs an additional layer between:

- plugin
- tool

That layer is:

- `tool_group`

## 7. Recommended Authorization Model

The long-term model should become:

```text
plugin
  -> tool_group
    -> tool
```

Suggested Playwright example:

- `official/playwright`
  - `browser_read`
  - `browser_interact`
  - `browser_sensitive`
  - `browser_runtime`

Each group can define:

- `required_role`
- `allowed_groups`
- `session_scope`
- `side_effect_policy`
- `audit_level`

This keeps compatibility with the existing RBAC model while making mixed-risk MCP servers manageable.

## 8. Session Scope Model

Once Nexus moves beyond public read-only browser access, MCP session scope becomes a first-class concept.

Suggested scope types:

- `global`
- `user`
- `group`
- `service_account`

### 8.1 `global`

Used only for safe shared state.

Examples:

- public read-only browser access
- server-level utility sessions

### 8.2 `user`

The most important target scope.

Each Nexus user gets their own isolated MCP-side session state.

Examples:

- browser login state
- Lark user auth
- GitHub personal token scope

### 8.3 `group`

Useful later for shared team/service contexts.

### 8.4 `service_account`

Used when Nexus intentionally acts as a service principal rather than an end user.

This must be explicit and auditable.

## 9. Recommended Nexus-Side Abstraction

Nexus should eventually introduce a reusable layer such as:

- `MCPSessionManager`

This should be separate from `MCPManager`.

### 9.1 `MCPManager`

Should remain responsible for:

- connecting to MCP servers
- registering tool schemas
- maintaining transport/session lifecycles at the server connection layer

### 9.2 `MCPSessionManager`

Should become responsible for:

- mapping Nexus user -> MCP session scope
- creating/retrieving per-user MCP session state
- managing storage state references or credential references
- expiration / cleanup
- explicit revocation
- auditing session ownership

This separation matters because transport management and user identity isolation are different concerns.

## 10. Proposed Data Model Direction

The long-term session binding model can look like:

```text
plugin instance
  + session scope
  + nexus user id
  + remote session id (optional)
  + credential ref
  + state ref
  + expires_at
  + last_used_at
  + auth level
```

Potential fields:

- `plugin_id`
- `scope_type`
- `scope_owner_id`
- `remote_session_id`
- `credential_secret_id`
- `state_blob_ref`
- `auth_level`
- `status`
- `expires_at`
- `last_used_at`

This model is intentionally generic and should work for browser storage state, OAuth-backed MCP sessions, and remote server session identifiers.

## 11. Browser-Specific Implications

Playwright becomes the first concrete adopter of the generic MCP session model.

### 11.1 Phase A Browser Behavior

Browser behavior should be:

- public
- stateless
- read-only

That means:

- no login persistence
- no user cookie reuse
- no authenticated interaction by default

### 11.2 Phase B Browser Behavior

Each authenticated browser user should receive:

- isolated browser context
- isolated cookies / local storage / session storage
- isolated tabs/page state
- explicit audit attribution

The Nexus-side mapping should be:

```text
Nexus user
  -> MCPSessionManager
  -> Playwright session scope (user)
  -> isolated browser context
```

This prevents:

- cross-user login leakage
- session contamination
- ambiguous audit trails

## 12. Operational Rules

### 12.1 Default Safety Rule

If Nexus cannot prove that a browser action is using an isolated session owned by the requesting user, it must not treat the action as authenticated.

### 12.2 Public Read Rule

Public read access may remain shared at the plugin/server layer so long as:

- no authenticated state is reused
- no user-owned secrets are attached

### 12.3 Authenticated Action Rule

Any browser action that depends on login, persistence, or stored credentials must require:

- isolated session scope
- stricter tool-group policy
- stronger audit visibility

## 13. Implementation Sequence

### Step 1: Stabilize Public Browser Read

Implement now:

- Playwright as a built-in browser plugin
- only public stateless browsing
- tool-group split with read-only default exposure

### Step 2: Add Tool Group Policy

Implement next:

- plugin-level `tool_groups`
- group-level `required_role` and `allowed_groups`
- make Playwright the first grouped MCP plugin

### Step 3: Introduce `MCPSessionManager`

Implement after the public-read phase is stable:

- generic session binding layer for MCP plugins
- support `scope=user`
- store session ownership and state references in Nexus

### Step 4: Enable Authenticated Browser Sessions

Only after the session layer exists:

- per-user browser sessions
- per-user authenticated page access
- eventually restricted interaction tools

### Step 5: Reuse The Pattern For Other MCP Plugins

After browser is proven:

- reuse the same session isolation model for future identity-bearing MCP integrations

## 14. Immediate Recommendation

The immediate recommendation for the current repository is:

1. Treat Playwright as a built-in public-read browser plugin.
2. Do not allow implicit login/session reuse.
3. Introduce Playwright tool groups before enabling broader browser actions.
4. Design the next stage as a generic `MCPSessionManager`, not as a Playwright-specific hack.

## 15. Decision Summary

The core design decisions are:

- browser support starts as stateless public read
- authenticated browser usage must be per-user isolated
- session isolation belongs in Nexus, not as an implicit side effect of MCP transport
- the solution should generalize to future MCP plugins
- Playwright should be the first adopter of a reusable MCP session architecture, not the only one
