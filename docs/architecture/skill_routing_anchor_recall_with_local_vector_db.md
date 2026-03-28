# Skill Routing Anchor Recall With Local Vector DB

## 1. Goal

Improve Nexus skill routing so natural user phrasing can reliably recall the correct skill, especially for cases where a single skill description is too thin.

The immediate motivating failure is:

- user asks: "你可以给我查一下最新的AI论文吗？给我汇总一下。"
- browser MCP is already connected and Playwright tools are registered
- but `route_skills()` does not match `web_browsing`
- so the turn-level toolbelt does not include any `browser_*` tools

This is a routing recall problem, not an MCP transport problem.

The recommended solution is:

**keep the current layered router, but upgrade skill recall from one-vector-per-skill to multi-anchor-per-skill, backed by a local vector database.**

For the current stack, the best local vector store is:

**Postgres + pgvector**

because the repo already uses it for memory storage and embedding search.

## 1.1 Current Status

The foundational storage and sync path described here is now partially implemented:

- skill routing anchors are stored in Postgres + pgvector
- runtime skill registration syncs anchors into the DB and prunes removed skills
- `routing_examples` survive restarts and participate in recall

That means this document should now be read as an optimization-and-consolidation document rather than as a greenfield design.

The next step is no longer "add anchors at all." The next step is:

- add domain/context pre-gate before recall
- add scope/group/policy prefilter before final tool injection
- make anchor recall one stage inside a larger unified routing/governance pipeline

## 2. Problem Summary

The current `SemanticToolRouter.register_skills()` embeds one synthesized description per skill:

- skill name
- description
- domain
- intent keywords

That works for obvious keyword overlap, but it is weak for:

- colloquial phrasing
- multilingual phrasing drift
- long-tail user intents
- ambiguous verbs like "查一下", "看一下", "搜一下", "汇总一下"
- tasks whose real intent is hidden in user outcome language rather than tool language

This is why `web_browsing` can miss queries such as:

- 最新 AI 论文
- 帮我看下 arXiv 最近有什么
- 去网上搜一下这个新闻
- 帮我总结微博热搜

even if the skill itself is actually the right execution path.

## 3. Design Principles

1. Preserve the current layered routing model rather than replacing it wholesale.
2. Improve recall first, then improve precision.
3. Keep the first implementation compatible with current skill cards and router APIs.
4. Use durable local storage for routing anchors instead of transient in-memory vectors only.
5. Make the design generic so it can support future MCP/skill growth, not just browser routing.

## 4. Proposed Architecture

### 4.1 Core Idea

Each skill should own multiple routing anchors instead of a single embedding.

Each anchor is a short text artifact that represents one way a user may ask for that skill.

Suggested anchor types:

- `description`
  - canonical skill description
- `keyword`
  - compact intent or domain phrases
- `synthetic_query`
  - LLM-generated natural user utterances
- `negative_hint`
  - optional future use for known confusions and exclusions

Routing then becomes:

1. embed the user query
2. search top anchors from local vector DB
3. aggregate anchor hits back to skills
4. select top skills by aggregated score
5. optionally rerank top skills before final binding

### 4.2 Why A Local Vector DB

Using a local vector DB is better than keeping anchors only in RAM because it enables:

- durable routing knowledge across restarts
- background refresh and re-indexing
- inspection of which anchors are driving matches
- offline evaluation and benchmark replay
- future admin tooling for routing quality analysis

For this repo, `pgvector` is the shortest-path choice because:

- PostgreSQL already exists in the stack
- `app/core/db.py` already ensures `CREATE EXTENSION vector`
- `app/models/memory.py` already uses `pgvector`
- operationally this is simpler than introducing a second vector system

## 5. Data Model

### 5.1 New Routing Anchor Record

Recommended logical schema:

```text
skill_routing_anchor
  id
  skill_name
  anchor_type
  language
  text
  weight
  source
  embedding
  enabled
  created_at
  updated_at
```

Recommended field meaning:

- `skill_name`
  - stable link back to the loaded skill card
- `anchor_type`
  - `description` | `keyword` | `synthetic_query` | later `negative_hint`
- `language`
  - for bilingual or multilingual tuning
- `text`
  - actual anchor content
- `weight`
  - allows description and validated anchors to count more than weak synthetic samples
- `source`
  - `skill_frontmatter`, `generated`, `manual`, `benchmark_feedback`
- `embedding`
  - `Vector(EMBEDDING_DIMENSION)`
- `enabled`
  - operational kill switch for bad anchors

### 5.2 Skill Metadata Extension

Skill cards should gain an explicit routing metadata section in frontmatter.

Recommended additive fields:

```yaml
routing_examples: [
  "你可以帮我查一下最新的AI论文吗",
  "帮我看一下最近 arXiv 上有什么新论文",
  "去网上搜一下这个主题最近的进展",
  "帮我汇总一下微博热搜"
]
routing_domains: ["web", "search", "research"]
routing_weight: 1.0
```

Important note:

- this should be additive
- existing `intent_keywords`, `routing_hints`, and `required_tools` should continue to work

## 6. Retrieval Flow

### 6.1 Phase-1 Recall Flow

Recommended near-term flow:

1. run existing fast intent/domain gate
2. load candidate skill domains if available
3. vector search top-N anchors from `skill_routing_anchor`
4. group hits by `skill_name`
5. aggregate score per skill
6. apply role filtering
7. take top-K skills above threshold
8. inject skill-bound tools as today

### 6.1.1 Updated Relationship To The Current Runtime

The next runtime target should refine this order to:

1. domain/context pre-gate
2. scope/group/policy prefilter
3. anchor recall
4. skill aggregation
5. worker-aware tool shaping
6. call-time enforcement

So anchor recall remains important, but it should not keep expanding as an isolated subsystem.

### 6.2 Skill Score Aggregation

One practical starting formula:

```text
skill_score =
  max(anchor_similarity * anchor_weight)
  + 0.20 * top3_anchor_mean
  + 0.10 * domain_bonus
```

Why this shape:

- `max(...)` preserves the best anchor hit
- `top3_anchor_mean` rewards skill consistency instead of one accidental match
- `domain_bonus` keeps compatibility with the current domain/context affinity logic

### 6.3 Later Precision Layer

Once recall improves, precision can be improved with a second-stage reranker:

- input: user query + top recalled skill summaries
- model: local reranker or lightweight cross-encoder
- output: reranked top 3-5 skills

This should be optional in the first implementation.

## 7. Synthetic Query Generation Strategy

### 7.1 Generation Timing

Do not generate synthetic queries on the hot path.

Generate them:

- at skill registration/update time
- via an admin maintenance command
- or via an offline refresh job

### 7.2 Generation Sources

Recommended sources in priority order:

1. manual curated examples in skill frontmatter
2. deterministic templates from `intent_keywords`
3. LLM-generated synthetic queries
4. later, validated runtime queries from real traffic

### 7.3 Safety Rules

Generated routing examples should be:

- short
- user-language oriented
- capability-descriptive rather than policy-expansive
- reviewed or rate-limited before becoming authoritative

Avoid generating anchors that imply permissions the skill does not actually have.

## 8. Why Pgvector Is The Right First Choice

### 8.1 Operational Fit

The repo already runs Postgres and already depends on `pgvector`, so adding a routing-anchor table is much lower risk than introducing:

- Qdrant
- Milvus
- Chroma
- FAISS sidecar files

### 8.2 Product Fit

Routing quality should be inspectable and debuggable alongside the rest of Nexus state.

Keeping anchor storage in the main application database makes it easier to build:

- admin inspection pages
- offline benchmark reports
- skill quality dashboards
- audit trails for anchor generation or disabling

### 8.3 Performance Fit

The expected number of skills is still small enough that pgvector is more than sufficient for:

- a few hundred skills
- tens of anchors per skill
- low-latency top-K recall

This can later be revisited only if routing scale becomes dramatically larger.

## 9. Recommended Implementation Plan

### P0: Document And Extend Skill Metadata

Goal:

- keep current router working
- start capturing better routing examples immediately

Tasks:

- extend skill metadata format to support `routing_examples`
- update `SkillLoader` to parse and expose routing examples
- add curated examples to high-value skills such as `web_browsing`

Expected outcome:

- we can improve routing quality even before DB persistence is complete

### P1: Introduce Persistent Skill Anchor Storage In Pgvector

Goal:

- move from one in-memory vector per skill to durable multi-anchor recall

Tasks:

- add `SkillRoutingAnchor` SQLModel
- create migration / table initialization path
- add indexing job or startup sync to embed anchors
- store:
  - description anchor
  - keyword anchors
  - routing example anchors

Expected outcome:

- stable local vector recall across restarts

### P2: Aggregate Anchor Hits Back To Skills

Goal:

- make `route_skills()` use anchor recall instead of direct skill-vector cosine only

Tasks:

- add anchor search helper
- aggregate by `skill_name`
- preserve role filtering and thresholding
- log top anchor hits for wire-log debugging

Expected outcome:

- much better recall for natural phrasing such as browser/research/search requests

### P3: Add Optional Reranker And Benchmark Loop

Goal:

- improve precision without sacrificing recall

Tasks:

- add local reranker on top recalled skills
- add routing benchmark set
- compare current router vs anchor recall vs anchor recall + reranker

Expected outcome:

- routing quality becomes measurable rather than anecdotal

## 10. Immediate Application To `web_browsing`

The first skill that should use this system is `web_browsing`.

Recommended initial routing examples:

- 帮我查一下最新的 AI 论文
- 帮我看看最近 arXiv 上有什么重要论文
- 去网上搜一下这个主题最近的新闻
- 帮我汇总一下微博热搜
- 帮我打开网页看一下这个内容
- 帮我截图这个页面

This is the fastest way to fix the current observed failure mode where the browser tools are available globally but not selected for the turn.

## 11. Recommended Technical Direction

For this repo, the recommended path is:

1. keep the current layered semantic router
2. add multi-anchor skill metadata
3. store anchors in local Postgres + pgvector
4. aggregate recall by skill
5. later add a local reranker only if precision still needs help

This is the most repo-aligned, lowest-friction, and most observable architecture.

## 12. Open Design Questions

These can be decided during implementation:

- whether anchor sync happens eagerly at startup or via explicit admin refresh
- whether generated examples should be stored back into skill files or only into DB
- whether `tool_router` should keep a hot in-memory cache on top of pgvector query results
- whether benchmark-validated runtime queries can automatically promote to durable anchors

## 13. Final Recommendation

Yes, the sample matching layer should use a local vector database.

For the current Nexus project, that local vector database should be:

**the existing Postgres stack with pgvector, not a separate new vector service.**

That gives us:

- the shortest implementation path
- durable routing memory
- good enough performance
- easier debugging
- strong alignment with the current codebase

So the next practical engineering sequence should be:

1. add `routing_examples` to skill metadata
2. create a pgvector-backed `skill_routing_anchor` table
3. switch `route_skills()` from one-vector-per-skill to anchor aggregation
4. benchmark the improvement using browser-heavy and natural-language queries
