# Multi-Model Execution Strategy

> Status: Direction Draft
> Date: 2026-03-14
> Intent: Reserve a future-ready design for multi-model execution without raising it above current P0 priorities.

## 1. Why This Exists

Nexus already has a worker-oriented execution architecture:

- `skill_worker`
- `code_worker`
- `reviewer_worker`
- `WorkerDispatcher`

That architecture creates a natural place to introduce **multiple model roles** later.

However, the current project priority is still:

1. Home Assistant reliability
2. Binding / login / permission experience
3. Message-first usability through Telegram + Web fallback

So the near-term strategy is:

**Use one stable primary API model first, make the main product loop reliable, and defer true multi-model execution until the P0 baseline is proven.**

This document exists so the future implementation does not need to restart from first principles.

---

## 2. Current Decision

### 2.1 Near-Term Runtime Strategy

For the current phase, Nexus should prefer:

- **one primary remote/API model** for core execution
- optional local models only for experiments or low-risk auxiliary use
- no required multi-model orchestration in the production-critical path

This means:

- Home Assistant core flows should run on the most stable model available
- binding/login/permission UX should not depend on advanced model routing
- daily-use reliability is more important than local-cost optimization right now

### 2.2 What Is Explicitly Deferred

The following are intentionally delayed:

- per-worker model routing in production
- per-skill model overrides in production
- true multi-agent, multi-model delegation loops
- local model fallback for high-risk execution by default
- model specialization that increases debugging complexity before the single-model baseline is stable

---

## 3. Long-Term Direction

The future target is not "many models everywhere."

The future target is:

**assign the right model to the right execution responsibility, with clear governance, fallback behavior, and observability.**

The intended evolution path is:

1. single stable primary model
2. worker-level model selection
3. skill-level override where justified
4. optional local/remote hybrid optimization

This should happen only after the runtime has stable behavior under real P0 usage.

---

## 4. Preferred Future Model Layers

### 4.1 Primary Execution Model

A stable remote/API model should remain the default for:

- `skill_worker` execution in important flows
- `code_worker` execution
- high-risk tool calling
- reviewer-sensitive paths

This model should optimize for:

- tool-calling stability
- lower hallucination rate
- stronger code generation and repair behavior
- reliable instruction following

### 4.2 Auxiliary / Local Model

A smaller local model may later assist with:

- lightweight summarization
- low-risk chat
- memory classification
- inexpensive routing support
- non-critical rewrite or formatting tasks

This model should **not** become the default for:

- Home Assistant execution
- code repair loops
- reviewer-critical validation
- permission-sensitive decisions

unless later evidence proves that it is reliable enough.

### 4.3 Reviewer-Sensitive Model

If Nexus later separates reviewer behavior more strongly, reviewer-critical paths may deserve either:

- the same stable primary execution model, or
- a dedicated stronger model tier

This decision should only be made when reviewer behavior is fully graph-native and there is evidence that validation quality is a bottleneck.

---

## 5. Recommended Future Routing Model

The recommended order of model choice should be:

1. worker-level default
2. skill-level override
3. risk-level override
4. fallback override

### 5.1 Worker-Level Default

Example future shape:

- `skill_worker -> stable_remote_model`
- `code_worker -> stable_remote_model`
- `reviewer_worker -> stable_remote_model`
- low-risk `chat_worker -> local_or_remote_light_model`

Worker-level routing should be the default because it is easier to reason about than arbitrary task-level switching.

### 5.2 Skill-Level Override

Some skills may later require explicit override.

Example:

- `homeassistant -> force stable remote model`
- `web_browsing -> stable remote model`
- low-risk summary skill -> local model allowed

This should only be used when a skill has clear reliability or cost characteristics that justify a different model.

### 5.3 Risk-Level Override

Future model routing may also take into account:

- `risk_level`
- `side_effect`
- `requires_verification`

For example:

- low-risk read-only tasks may allow cheaper models
- high-risk action flows should stay on the most stable model tier

### 5.4 Fallback Override

If a worker repeatedly fails on a weaker model, the system may later escalate to a stronger one.

This should be bounded and observable, never silent or uncontrolled.

---

## 6. Governance Rules for Future Multi-Model Execution

When Nexus introduces multi-model routing, it should follow these rules:

1. **No hidden model switching in risky flows**
   - model escalation must be visible in logs and trace data

2. **Worker boundaries come before model cleverness**
   - do not use multi-model routing as a substitute for poor worker design

3. **High-risk action paths default to the most reliable model**
   - especially Home Assistant and permission-sensitive operations

4. **Local model use must be opt-in for critical paths**
   - not the default

5. **Every model decision must be explainable after the fact**
   - logs should make it obvious why a certain model handled a path

6. **Cost optimization must not outrank reliability during P0**
   - P0 is about proving real usefulness first

---

## 7. Observability Requirements

Before production multi-model execution is enabled, traces should include:

- selected model name
- selected worker
- selected skill
- why that model was chosen
- whether fallback or escalation happened
- whether the route was local or remote

The existing FLOW / WIRE logging model should be extended rather than replaced.

---

## 8. Suggested Future Configuration Shape

This is only a direction sketch, not a final schema.

Possible future layers:

- global primary model
- worker defaults
- optional skill overrides
- optional escalation target

Example conceptually:

- `default_model = remote_primary`
- `worker_models.skill_worker = remote_primary`
- `worker_models.code_worker = remote_primary`
- `worker_models.reviewer_worker = remote_primary`
- `worker_models.chat_worker = local_light`
- `skill_models.homeassistant = remote_primary`

The real schema should be decided later based on existing config conventions.

---

## 9. Preconditions Before Implementation

Do not implement full multi-model execution until these are true:

1. Home Assistant P0 flows are stable on a single primary model
2. binding/login/permission experience is no longer the main friction
3. Telegram + Web fallback experience is acceptable for daily use
4. worker boundaries are stable enough that model routing does not hide architecture problems
5. logs and audit traces can clearly show model choice and fallback behavior

---

## 10. Recommended Future Rollout Order

When the project is ready, the rollout should happen in this order:

1. Add configuration support for worker-level model defaults
2. Add trace logging for model selection decisions
3. Enable local model only for low-risk chat or summary paths
4. Evaluate worker-level remote/local split
5. Add skill-level overrides only where real evidence justifies them
6. Consider stronger reviewer-specific routing only if validation quality becomes a bottleneck

---

## 11. Current Recommendation

For now, Nexus should:

- use one stable API model as the primary execution model
- keep local models out of the main Home Assistant execution path
- defer multi-model orchestration to a later phase
- revisit this document after P0 reliability goals are met

That is the best tradeoff between:

- reliability
- debugging clarity
- implementation cost
- future extensibility
