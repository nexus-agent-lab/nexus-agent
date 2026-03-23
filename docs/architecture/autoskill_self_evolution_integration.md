# AutoSkill-Inspired Skill Self-Evolution Integration

## 1. Why This Matters

`AutoSkill` proposes a practical direction: do not treat user experience as disposable chat history, and do not force everything into long-context memory retrieval. Instead, abstract recurring experience into reusable skills, evolve them over time, and inject the right skills into future requests without retraining the base model.

That direction fits this repository well because the system already has three partial building blocks:

- skill cards loaded by `SkillLoader`
- a `MemSkillDesigner` that can evolve prompt templates offline
- a `skill-learning` flow that can append learned rules to a skill card after review

The gap is that these pieces are not yet unified into a single lifecycle. Today, the system can:

- generate or edit a skill card
- append a learned rule
- evolve a memory-processing prompt

But it does not yet consistently:

- extract stable experience into a normalized skill artifact
- decide whether the learned result should be a rule, a routing hint, a procedure, or a memory skill prompt update
- inject learned knowledge at the right stage of the runtime graph
- close the loop with structured verification and longitudinal metrics

## 2. Key Design Principle

For this system, the best interpretation of AutoSkill is:

`experience -> normalized lesson -> skill patch candidate -> canary/approval -> runtime injection -> feedback -> re-evolution`

This is better than a pure memory approach because many failures here are procedural, not factual. For example:

- choosing the wrong tool before discovery
- skipping a verification step
- using a valid tool in the wrong sequence
- failing to ask a clarification question when `permission_denied` or `invalid_input` is returned

Those are best captured as skill behavior updates, not as free-form memory snippets.

## 3. Current System Mapping

### 3.1 Existing Components

- `app/core/skill_loader.py`
  - loads skill cards
  - exposes routing hints and required tools
  - can append learned rules to a `## Learned Rules` section
- `app/core/designer.py`
  - evolves `MemorySkill.prompt_template`
  - uses recent samples and canary tests
- `app/api/skill_learning.py`
  - stores `SkillChangelog`
  - supports approve/reject
- `app/core/result_classifier.py`
  - already normalizes runtime outcomes into categories such as `invalid_input`, `wrong_tool_or_domain`, `permission_denied`, and `verification_failed`
- `app/core/worker_graphs/skill_worker.py`
  - already distinguishes `discover`, `read`, `act`, `verify`

### 3.2 Architectural Opportunity

The document `docs/architecture/langgraph_skill_worker_migration.md` already points in the right direction: the designer should consume normalized runtime classifications instead of inventing a separate failure vocabulary.

That means this repository does not need a brand-new learning system first. The cleanest cut-in point is:

1. keep the current runtime graph
2. attach a unified lesson extractor after result classification
3. route extracted lessons to the correct evolution target

## 4. Proposed New Layer: Skill Evolution Engine

Introduce a new offline orchestration layer:

- `SkillEvolutionEngine`

Responsibility:

- consume structured traces, tool outcomes, reviewer results, and user corrections
- decide what kind of knowledge was learned
- produce a typed patch candidate
- send the patch into the existing approval flow

This should sit conceptually above:

- `MemSkillDesigner`
- `learn_skill_rule`
- skill card save/edit APIs

And below:

- raw runtime traces
- user feedback
- reviewer verification

## 5. Unified Skill Patch Model

The core design change is to stop treating all learning as "append one rule string".

Add a unified patch schema, for example:

```json
{
  "target_type": "skill_card|memory_skill|routing_hint|tool_policy",
  "target_name": "homeassistant",
  "patch_kind": "append_rule|rewrite_section|update_metadata|update_prompt_template",
  "trigger_category": "invalid_input",
  "confidence": 0.81,
  "evidence": [
    {
      "trace_id": "abc",
      "summary": "list_entities should have been called before act"
    }
  ],
  "before": "...",
  "after": "...",
  "reason": "Recurring failure across 11 traces",
  "status": "pending"
}
```

This is the key bridge from the paper to this system. It lets the same lifecycle manage different knowledge surfaces:

- skill card rule updates
- skill routing metadata updates
- memory skill prompt evolution
- future tool policy patches

## 6. What Should Be Learned Here

Not every repeated failure should become a skill update. The engine should classify lessons into four buckets.

### 6.1 Behavioral Rule

Use when the lesson is procedural and stable.

Examples:

- "For ambient temperature questions, run discovery first and filter non-room sensors."
- "If a tool returns permission denied, stop and ask the user instead of retrying."

Best target:

- skill card `Critical Rules` or `Learned Rules`

### 6.2 Execution Pattern

Use when the lesson is a multi-step pattern.

Examples:

- discover entities
- narrow candidates
- act
- verify

Best target:

- a structured section in the skill card, not a single bullet rule

### 6.3 Routing Hint

Use when the problem is pre-execution selection.

Examples:

- certain keywords should force `run_discovery`
- certain tasks should prefer `research_worker` over `skill_worker`

Best target:

- YAML frontmatter / routing metadata in the skill card

### 6.4 Memory Skill Prompt Evolution

Use when the issue is not action policy but content transformation quality.

Examples:

- fact extraction is too verbose
- retrieval summaries miss user preference emphasis

Best target:

- existing `MemorySkill.prompt_template` via `MemSkillDesigner`

## 7. Runtime Insertion Points

The lowest-risk implementation is to add learning hooks in three places.

### 7.1 After Result Classification

Input:

- `ResultClassification.category`
- tool metadata
- selected worker
- selected skill

Purpose:

- detect repeated structured failures

Good for:

- wrong-tool and missing-discovery lessons

### 7.2 After Reviewer / Verification

Input:

- whether task outcome was actually correct
- what mismatch remained

Purpose:

- capture "looked successful but actually failed" lessons

Good for:

- missing verification patterns
- false completion patterns

### 7.3 After Explicit User Correction

Input:

- "不是这个意思"
- "你应该先列出来再执行"
- "以后别这么做"

Purpose:

- capture stable user-specific preferences or domain conventions

Good for:

- personalization
- phrasing constraints
- institution-specific workflows

## 8. How The Designer Should Evolve

The current `MemSkillDesigner` is prompt-centric. For AutoSkill-style integration, it should become patch-centric.

Recommended split:

- `MemorySkillDesigner`
  - keep current role
  - only optimize memory encoding/retrieval prompts
- `SkillEvolutionEngine`
  - generate broader patch candidates
- `SkillPatchReviewer`
  - validate whether a patch is safe, scoped, and non-duplicative

This avoids overloading one class with incompatible responsibilities.

## 9. Approval and Safety Model

This repository already has the right instinct: human review before activation. Keep that.

Recommended policy:

- low-risk patch types:
  - append rule to `Learned Rules`
  - can auto-apply only after repeated evidence and successful canary
- medium-risk patch types:
  - rewrite `Critical Rules`
  - update routing hints
  - require approval
- high-risk patch types:
  - change required tools
  - change verification policy
  - change action sequencing for side-effectful tools
  - require approval plus canary

Canary design:

- replay historical traces in shadow mode
- compare:
  - task success rate
  - number of unnecessary tool calls
  - retry count
  - clarification rate
  - verification pass rate

## 10. Data Model Changes

### 10.1 Replace or Extend `SkillChangelog`

Current `SkillChangelog` is too narrow because it assumes one rule string.

Extend it with:

- `target_type`
- `patch_kind`
- `target_name`
- `before_content`
- `after_content`
- `trigger_category`
- `evidence_json`
- `confidence`
- `canary_status`
- `applied_at`

### 10.2 Add Lesson Aggregation Table

Add an intermediate table such as `SkillLessonCandidate`:

- stores deduplicated recurring failures
- aggregates counts before generating a patch

This matters because a single bad run should not create a permanent skill mutation.

Suggested fields:

- `fingerprint`
- `skill_name`
- `worker_name`
- `failure_category`
- `lesson_type`
- `count`
- `last_seen_at`
- `sample_evidence_json`

## 11. Recommended First Cut

The best cut-in point is not "fully autonomous self-evolving skills". That is too broad for a first iteration.

Start with:

### Phase 1: Structured Lesson Logging

- convert runtime failures into normalized lesson candidates
- no direct mutation yet
- aggregate by fingerprint

Success criteria:

- we can answer "what repeated mistakes does each skill make?"

### Phase 2: Rule-Only Evolution

- only generate `append_rule` patches for existing skill cards
- keep approval manual
- no routing metadata rewrite yet

Success criteria:

- skills become better at procedural guardrails

### Phase 3: Routing-Hint Evolution

- allow designer to suggest frontmatter updates
- add stronger review because this affects selection before execution

Success criteria:

- fewer `wrong_tool_or_domain` and `run_discovery` misses

### Phase 4: Unified Skill Patch Engine

- merge skill-card, routing, and memory-skill evolution under one patch review UI

Success criteria:

- one learning lifecycle across all skill surfaces

## 12. Why This Fits This System Better Than A Pure AutoSkill Clone

This system is not a blank-slate agent runtime. It already has:

- worker specialization
- tool metadata
- skill cards
- memory skills
- admin approval

So the right design is not to import the paper literally. The right move is to reinterpret AutoSkill as a control-plane upgrade:

- use normalized runtime outcomes as experience
- convert recurring experience into typed skill patches
- inject the approved patches into existing skill and worker machinery

In short:

- keep the current runtime
- unify the learning surfaces
- make designer output structured patches instead of only prompt text

## 13. Concrete Cut-In Recommendation

If we only do one thing first, it should be:

Build `SkillLessonCandidate` + patch generation for `append_rule` on existing skill cards.

Reason:

- lowest implementation risk
- directly compatible with `learn_skill_rule`
- easy to expose in current admin UX
- creates the dataset needed for later routing-hint and memory-skill evolution

## 14. Open Questions

Before implementation, we should decide:

1. Is learning global, per-user, or per-tenant?
2. Should user-preference skills be isolated from domain-operation skills?
3. Can routing-hint patches auto-apply for low-risk read-only skills?
4. Should canary replay use historical traces only, or also synthetic task suites?
5. Do we want one unified review queue for all patch types, or separate queues for `memskill` and `skill-card` changes?

## 15. Proposed Decision

Recommended initial policy:

- scope learning to `global + optional user override`
- keep `MemSkillDesigner` focused on memory prompts
- add `SkillEvolutionEngine` for typed skill-card and routing patches
- launch with `rule-only`, `manual approval`, `historical-trace canary`

That gives the project a realistic AutoSkill-style entry point without destabilizing the current execution loop.
