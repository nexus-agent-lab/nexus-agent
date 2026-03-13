# LangGraph Migration: Skill Worker / Code Worker Architecture

## 1. Objective

Refactor the current agent loop into a true LangGraph orchestration system with:

1.  **Protocol isolation**: Core orchestration must not depend on MCP protocol details or specific MCP server names.
2.  **Worker specialization**: Route requests to generic workers (`skill_worker`, `code_worker`, etc.) instead of hardcoding domain-specific executors like Home Assistant.
3.  **Deterministic recovery**: Replace soft prompt-only retry loops with explicit result classification, retry budgets, worker switching, and handoff conditions.
4.  **Hybrid routing**: Avoid both "vector-only blindness" and "LLM on every turn" latency by using deterministic intent gating first, then selective escalation.

This design is intended to solve the current failure modes:

- Tool calls repeat with the same invalid arguments after failure.
- The agent can enter recursive loops after Python execution or upstream tool errors.
- Vector-only routing is weak for short commands, mixed-domain requests, and cross-skill intent.
- LLM-based intent decomposition is too slow to run as the default path for every turn.

---

## 2. Core Principle

**The LangGraph core should understand capabilities, workers, and execution outcomes. It should not understand MCP protocol internals.**

That means:

- `MCPManager` remains the integration layer.
- Registered tools expose a unified metadata contract.
- The graph routes by worker and capability, not by MCP server name.
- Tool execution results are normalized before the graph reasons about them.

This preserves the existing plugin/MCP registration model while allowing the graph layer to become much more strict and deterministic.

---

## 3. Layered Architecture

```mermaid
flowchart TD
    A["User Message"] --> B["Supervisor Graph"]

    subgraph Core["Core Orchestration"]
        B --> C["Intent Gate"]
        C --> D["Worker / Skill Selection"]
        D --> E["Execution Plan"]
        E --> F["Dispatch Worker"]
        F --> G["Result Classifier"]
        G --> H["Reviewer Worker"]
        H --> I["Reply / Handoff"]
    end

    subgraph Workers["Worker Layer"]
        F --> SW["skill_worker"]
        F --> CW["code_worker"]
        F --> RW["research_worker"]
        F --> TW["chat_worker"]
    end

    subgraph Integration["Integration Layer"]
        SW --> TC["Tool Catalog"]
        CW --> TC
        RW --> TC
        TW --> TC
        TC --> TE["Tool Executor"]
        TE --> MM["MCPManager / Static Tools"]
    end
```

### 3.1 Integration Layer

Owns:

- MCP connectivity
- Tool registration
- schema conversion
- metadata injection
- low-level tool execution

Files:

- `app/core/mcp_manager.py`
- `app/core/tool_catalog.py`
- `app/core/tool_executor.py`

### 3.2 Core Orchestration Layer

Owns:

- fast intent gating
- worker selection
- skill selection
- execution planning
- retry budgets
- result classification
- reviewer approval
- handoff decisions

Files:

- `app/core/agent.py`
- `app/core/intent_gate.py`
- `app/core/result_classifier.py`

### 3.3 Worker Layer

Owns:

- skill-scoped execution
- code execution / repair loops
- research or chat-specific execution styles

Files:

- `app/core/worker_graphs/skill_worker.py`
- `app/core/worker_graphs/code_worker.py`
- `app/core/worker_graphs/research_worker.py`
- `app/core/worker_graphs/chat_worker.py`
- `app/core/worker_graphs/reviewer_worker.py`

### 3.4 Optimization Layer

Owns:

- offline analysis of failures
- prompt evolution
- skill quality analysis

Files:

- `app/core/designer.py`

The designer should consume normalized runtime classifications instead of inventing a separate failure vocabulary.

---

## 4. Worker Model

The system should route to generic workers rather than domain-specific executors.

### 4.1 `skill_worker`

Purpose:

- Execute tasks through skills plus registered tools.
- Load skill rules, bind skill-specific toolbelts, run discovery when needed, then act/read/verify.

Examples:

- Home Assistant
- Feishu / Lark
- browser automation
- future MCP-backed integrations

The graph should never hardcode `homeassistant` as a worker. It should select:

- `selected_worker = "skill_worker"`
- `selected_skill = "homeassistant"`

### 4.2 `code_worker`

Purpose:

- Execute code-centric or sandbox-centric loops with stronger control over retries, repair, and verification.

Examples:

- `python_sandbox`
- data transformation
- code generation + execution
- future shell / SQL / browser-script workflows

This worker exists because code execution needs a stronger closed loop than generic skill execution:

- generate
- precheck
- execute
- classify failure
- repair if allowed
- verify outputs

### 4.3 `research_worker`

Purpose:

- Read-only exploration, documentation lookup, retrieval-heavy tasks, or cross-source comparison.

This worker should avoid side effects.

### 4.4 `chat_worker`

Purpose:

- Lightweight direct-answer flow for simple conversational tasks or low-risk tool use.

### 4.5 `reviewer_worker`

Purpose:

- Validate whether the goal was actually reached.
- Validate side effects where required.
- Enforce stop conditions and reject hallucinated completion.

This worker should be read-only and mandatory for risky or multi-step flows.

---

## 5. Tool Metadata Contract

All registered tools should expose a unified capability metadata contract. The graph layer should only depend on this contract, not on MCP-specific details.

```python
class ToolCapabilityMetadata(TypedDict, total=False):
    tool_name: str
    capability_domain: Literal[
        "home_automation",
        "code_execution",
        "memory",
        "knowledge",
        "communication",
        "system",
        "generic",
    ]
    operation_kind: Literal[
        "discover",
        "read",
        "act",
        "transform",
        "verify",
        "notify",
    ]
    side_effect: bool
    risk_level: Literal["low", "medium", "high"]
    retry_policy: Literal["never", "safe_once", "bounded"]
    max_retries: int
    requires_verification: bool
    supports_dry_run: bool
    preferred_worker: Literal[
        "chat_worker",
        "skill_worker",
        "code_worker",
        "research_worker",
        "reviewer_worker",
    ]
    context_tags: list[str]
    allowed_groups: list[str]
    required_role: str
```

### Metadata Notes

- `preferred_worker` is the graph-facing routing hint.
- `capability_domain` must represent business capability, not MCP transport or server name.
- `operation_kind` lets the graph distinguish discovery from act/read/verify logic.
- `retry_policy` and `max_retries` provide hard execution constraints.
- `requires_verification` allows the reviewer to be enforced automatically.

### Registration Rule

`MCPManager` and static tool registration should both populate the same metadata shape.

This prevents special-case branching for MCP vs local tools later in the graph.

---

## 6. Runtime Outcome Contract

All tool executions should be normalized before the graph interprets them.

```python
class ToolExecutionOutcome(TypedDict, total=False):
    tool_name: str
    worker: str
    status: Literal["success", "error"]
    raw_text: str
    structured_data: dict | list | None
    exception_text: str | None
    latency_ms: float
    fingerprint: str
    metadata: ToolCapabilityMetadata
```

### Key Rule

`fingerprint` must be stable for "same tool call, same normalized args".

Recommended composition:

- `tool_name`
- normalized args
- optionally selected skill

This enables the graph to prevent repeated identical failing calls.

---

## 7. Result Classification Contract

The graph should branch on a normalized result classification, not by parsing raw strings directly inside graph nodes.

```python
class ResultClassification(TypedDict, total=False):
    category: Literal[
        "success",
        "invalid_input",
        "wrong_tool_or_domain",
        "permission_denied",
        "retryable_upstream_error",
        "retryable_runtime_error",
        "non_retryable_runtime_error",
        "unsafe_state",
        "verification_failed",
    ]
    retryable: bool
    should_switch_worker: bool
    requires_handoff: bool
    user_facing_summary: str
    debug_summary: str
    suggested_next_action: Literal[
        "retry_same_worker",
        "switch_worker",
        "run_discovery",
        "ask_user",
        "handoff",
        "verify",
        "complete",
    ]
```

### Runtime Use

The `result_classifier` should map execution outcomes into deterministic categories such as:

- entity not found -> `invalid_input` + `run_discovery`
- permission denied -> `permission_denied`
- repeated Python runtime error -> `retryable_runtime_error` or `non_retryable_runtime_error`
- dangerous device state -> `unsafe_state`

### Designer Integration

The existing Designer system should reuse these categories for offline analysis:

- aggregate failure distributions
- detect underperforming skills
- identify routing blind spots
- improve prompts, metadata, and skill definitions

This replaces duplicate failure vocabularies across runtime and offline systems.

---

## 8. Agent State Contract

The current state is too thin for deterministic recovery. The LangGraph state should be expanded to track workers, skills, attempts, and verification explicitly.

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user: Optional[User]
    trace_id: uuid.UUID
    session_id: Optional[int]

    intent_class: str | None
    route_confidence: float | None
    selected_worker: str | None
    candidate_workers: list[str] | None

    selected_skill: str | None
    candidate_skills: list[str] | None
    skill_rules: str | None
    skill_toolbelt: list[str] | None

    execution_mode: str | None
    current_plan: dict | None
    current_step: dict | None
    step_index: int
    remaining_steps: list[dict] | None

    memories: list[str] | None
    context: str

    attempts_by_node: dict[str, int]
    attempts_by_worker: dict[str, int]
    attempts_by_tool: dict[str, int]
    last_tool_fingerprint: str | None
    blocked_fingerprints: list[str] | None

    last_outcome: ToolExecutionOutcome | None
    last_classification: ResultClassification | None
    execution_history: list[dict] | None

    verification_status: Literal["pending", "passed", "failed"] | None
    requires_handoff: bool
    handoff_reason: str | None

    llm_call_count: int
    tool_call_count: int
```

### Important Fields

- `selected_worker`: graph routing target
- `selected_skill`: active skill inside `skill_worker`
- `attempts_by_tool`: bounded retries per tool or fingerprint
- `blocked_fingerprints`: prevents identical failure loops
- `last_classification`: deterministic branching state
- `verification_status`: separates "tool returned" from "task is actually complete"

---

## 9. Hybrid Routing Strategy

The routing system should be neither vector-only nor LLM-first.

### 9.1 Stage 1: Fast Intent Gate

`intent_gate.py` should run first using deterministic rules.

It should inspect:

- current user message
- recent user context
- previous failure classification
- current environment context (`home`, `work`, etc.)

It should output:

```python
class FastIntentDecision(TypedDict):
    intent_class: str
    candidate_workers: list[str]
    confidence: float
    needs_llm_escalation: bool
    needs_discovery: bool
    reason: str
```

Examples:

- "turn off bedroom light" -> `skill_worker`, high confidence
- "list available entities in living room" -> `skill_worker`, `needs_discovery=True`
- "parse this JSON in Python" -> `code_worker`
- "check docs and summarize design" -> `research_worker`

### 9.1.1 Important Constraint: Skill-Driven Routing Hints

The fast intent gate must not permanently hardcode domain keywords for optional integrations such as Home Assistant.

Temporary bootstrap patterns inside `intent_gate.py` are acceptable during the skeleton phase, but the production design should move domain matching into skill metadata.

Recommended direction:

- each installed skill exposes `routing_hints`
- the intent gate loads hints only from currently available skills
- worker and skill candidates are produced from those hints
- if a skill is not installed, its domain patterns do not participate in routing

Example shape:

```python
{
    "skill_name": "homeassistant",
    "routing_hints": {
        "keywords": ["light", "lamp", "entity", "device"],
        "discovery_keywords": ["list entities", "find device"],
        "preferred_worker": "skill_worker",
        "capability_domain": "home_automation",
    },
}
```

This keeps the routing layer generic and prevents the graph from drifting back into Home Assistant-specific assumptions.

### 9.1.2 Intent Gate Limitations and Planned Improvements

The initial `intent_gate.py` implementation is intentionally simple. It is a bootstrap layer, not the final routing system.

Current limitations:

- keyword matching is still shallow and phrase-based
- multilingual phrasing coverage is incomplete
- short commands can still be ambiguous
- compound tasks are only weakly detected by connector heuristics
- there is no learned weighting from historical routing outcomes yet

Planned improvements:

1.  **Skill-native routing hints**
    - move from plain `intent_keywords` to richer `routing_hints`
    - support aliases, discovery phrases, and negative hints

2.  **Weighted matching**
    - distinguish strong triggers from weak hints
    - score worker and skill candidates rather than simple inclusion

3.  **Phrase normalization**
    - normalize multilingual variants, room names, device aliases, and action verbs
    - improve handling of short voice-like commands

4.  **Historical feedback**
    - feed `last_classification` and persisted routing failures back into fast routing
    - down-rank repeated failure patterns

5.  **Hybrid skill recall**
    - combine deterministic hint matching with optional low-cost vector recall over skill metadata
    - keep full LLM escalation only for truly ambiguous cases

6.  **Skill installation awareness**
    - route only across currently installed or enabled skills
    - avoid domain assumptions when a skill is absent

These improvements should be tracked as follow-up work after the first deterministic routing integration is stable.

### 9.2 Stage 2: Skill or Mode Selection

If the selected worker is `skill_worker`, choose:

- `selected_skill`
- `candidate_skills`
- `skill_rules`
- `skill_toolbelt`

If the selected worker is `code_worker`, choose:

- execution mode
- code-specific toolbelt

### 9.3 Stage 3: LLM Escalation

LLM routing should be used only when needed:

- multiple workers match
- intent is mixed or compound
- routing confidence is below threshold
- previous step failed with `wrong_tool_or_domain`

This preserves accuracy without paying the LLM latency tax on every turn.

---

## 10. Supervisor Graph

Recommended top-level graph:

```mermaid
flowchart TD
    A["load_context"] --> B["classify_intent_fast"]
    B --> C["select_worker_candidates"]
    C --> D{"need_escalation?"}
    D -->|yes| E["llm_route_escalation"]
    D -->|no| F["select_skill_or_mode"]
    E --> F
    F --> G["build_execution_plan"]
    G --> H["dispatch_worker"]
    H --> I["classify_result"]
    I --> J{"next action"}
    J -->|complete| K["reviewer_worker"]
    J -->|retry| L["recover_or_replan"]
    J -->|switch worker| L
    J -->|handoff| M["final_reply"]
    K -->|pass| M
    K -->|fail| L
    L -->|continue| H
    L -->|handoff| M
```

### Node Responsibilities

- `load_context`: session history, summary, memory, user policy
- `classify_intent_fast`: deterministic routing gate
- `select_worker_candidates`: worker shortlist
- `llm_route_escalation`: only for ambiguous cases
- `select_skill_or_mode`: choose skill or execution mode
- `build_execution_plan`: define current step and success criteria
- `dispatch_worker`: call worker subgraph
- `classify_result`: convert outcome to normalized classification
- `recover_or_replan`: retry, switch worker, ask user, or handoff
- `reviewer_worker`: final verification gate
- `final_reply`: respond to user

---

## 11. Worker Subgraphs

### 11.1 `skill_worker`

```mermaid
flowchart TD
    A["load_skill_context"] --> B["bind_skill_toolbelt"]
    B --> C["discovery_if_needed"]
    C --> D["execute_skill_step"]
    D --> E["return_outcome"]
```

Responsibilities:

- load active skill instructions
- bind required/preferred/discovery tools
- keep tool scope narrow
- run discovery before side effects when required

The worker should not know whether tools came from MCP or static registry.

### 11.2 `code_worker`

```mermaid
flowchart TD
    A["prepare_code_task"] --> B["precheck"]
    B --> C["execute_code"]
    C --> D["classify_exec_result"]
    D --> E{"repairable?"}
    E -->|yes| F["repair_code"]
    F --> C
    E -->|no| G["verify_output_or_fail"]
```

Responsibilities:

- code generation or transformation
- precheck and static sanity validation
- execution in sandbox
- bounded repair loop
- artifact or output verification

### 11.3 `reviewer_worker`

Responsibilities:

- confirm the goal was actually achieved
- confirm required side effects happened
- detect unsafe or unverifiable completion
- block hallucinated "done" responses

This worker should be mandatory for:

- high-risk actions
- multi-step plans
- code execution tasks
- anything with `requires_verification=True`

---

## 12. Recovery Rules

The new system must use hard graph rules instead of pure prompt-based retries.

Transition note:

- during migration, retry and reflexion logic may use normalized `last_classification` as the primary signal
- raw `ToolMessage` string inspection remains as a temporary fallback for backward compatibility
- once worker subgraphs fully own execution outcomes, string-based fallback should be reduced or removed

### 12.1 Fingerprint Blocking

- If the same fingerprint fails twice, do not allow the identical call again in the same run.

### 12.2 Worker Budgets

- If `attempts_by_worker[selected_worker] >= 3`, force worker switch or handoff.

### 12.3 Tool Budgets

- Respect `retry_policy` and `max_retries` from metadata.
- `permission_denied` -> never retry
- `unsafe_state` -> handoff
- `wrong_tool_or_domain` -> switch worker or trigger LLM reroute
- `retryable_upstream_error` -> bounded retry with backoff
- `verification_failed` -> either repair or handoff

### 12.4 Completion Rule

No worker may claim completion unless one of the following is true:

- reviewer passed
- verification node passed
- task is explicitly a conversational answer that does not require external verification

---

## 13. File Plan

Recommended new or refactored files:

- `app/core/tool_metadata.py`
- `app/core/tool_catalog.py`
- `app/core/tool_executor.py`
- `app/core/result_classifier.py`
- `app/core/intent_gate.py`
- `app/core/worker_graphs/skill_worker.py`
- `app/core/worker_graphs/code_worker.py`
- `app/core/worker_graphs/research_worker.py`
- `app/core/worker_graphs/chat_worker.py`
- `app/core/worker_graphs/reviewer_worker.py`
- `app/core/agent.py`

Existing files that should remain focused:

- `app/core/mcp_manager.py`: integration only
- `app/core/designer.py`: offline optimization only

---

## 14. Migration Phases

### Phase 1: Contracts + Classification

Goal:

- Introduce capability metadata, execution outcome, and result classification without fully replacing the current graph.

Tasks:

1. Add metadata contract support to tool registration.
2. Add `tool_executor`.
3. Add `result_classifier`.
4. Replace raw string error interpretation where possible.

### Phase 2: Fast Intent Gate

Goal:

- Replace default LLM-first routing with deterministic routing plus selective escalation.

Tasks:

1. Add `intent_gate.py`.
2. Introduce `selected_worker`, `selected_skill`, and routing confidence into state.
3. Keep LLM intent routing only as an escalation path.

### Phase 3: Worker Subgraphs

Goal:

- Split the monolithic `agent` node into supervisor plus worker subgraphs.

Tasks:

1. Introduce `skill_worker`.
2. Introduce `code_worker`.
3. Introduce `reviewer_worker`.
4. Move execution and verification logic out of the monolithic main node.

### Phase 4: Reviewer Enforcement + Offline Feedback Loop

Goal:

- Enforce real stop conditions and feed normalized failures into Designer.

Tasks:

1. Make reviewer mandatory for risky and multi-step flows.
2. Persist normalized classification data.
3. Upgrade Designer to analyze shared classification categories.

---

## 15. Non-Goals

The following are explicitly out of scope for the first migration:

- Multi-model orchestration parity with projects like oh-my-opencode
- Replacing MCP registration with a new plugin protocol
- Rewriting all skills at once
- Eliminating semantic routing entirely

The immediate goal is to make the current system deterministic, composable, and safe under failure.

---

## 16. Decision Summary

This migration adopts the following decisions:

1.  The core graph will route by worker and capability, not by MCP server.
2.  `skill_worker` replaces domain-specific worker naming such as `ha_worker`.
3.  `code_worker` replaces Python-specific naming so the execution loop can expand beyond Python later.
4.  `result_classifier` becomes the shared runtime error vocabulary.
5.  `designer.py` should consume the same classification vocabulary for offline improvement.
6.  Intent routing becomes hybrid: deterministic first, selective LLM second.
7.  Verification and handoff become graph-level behavior, not just prompt instructions.
