# Skill Architecture Performance Analysis

## 1. Context
User asked: "Will hierarchical skill loading increase API calls? How does the current system compare to the OpenViking-inspired approach?"

## 2. Architecture Comparison

### A. Current System (Nexus Agent v2)
*   **Mechanism**: 
    1.  **L0 (Always On)**: Injects `SkillLoader.load_summaries()` (List of all skill names + descriptions).
    2.  **L1 (Activation)**: Python-based **Keyword Matching** (`intent_keywords` in Frontmatter).
*   **API Calls**: **1 per turn** (The final Chat Completion).
    *   *Note*: Keyword matching is local CPU logic.
*   **Token Usage**: 
    *   **Base**: Moderate (~200-500 tokens for summaries).
    *   **Active**: Adds full text of matched skills.
    *   **Risk**: If keywords are too broad (e.g. "task"), it dumps *everything* into context, spiking tokens.

### B. OpenViking-Inspired (Proposed: Vector/Score Propagation)
*   **Mechanism**:
    1.  **Router**: Use the existing `tool_router` (Semantic/Vector) to match User Query -> Skill Description.
    2.  **Selection**: Select Top-K skills based on semantic similarity score.
*   **API Calls**: **1 per turn** (Same as current).
    *   *Note*: We already generate an Embedding for Tool Routing. We re-use this vector for Skill Routing. No extra LLM call.
*   **Token Usage**: 
    *   **Base**: Can be reduced (hide summaries, only show categories).
    *   **Active**: High precision. Only relevant skills injected.
    *   **Benefit**: Better than keywords (e.g. "draw me a picture" matches "image_gen" skill even without "draw" keyword).

### C. OpenViking (Full/Planner Mode - NOT PROPOSED)
*   **Mechanism**:
    1.  **Planner LLM**: Ask LLM "What skills do I need?"
    2.  **Executor LLM**: Run the task.
*   **API Calls**: **2 per turn** (+100% cost/latency).
*   **Token Usage**: Low for Planner, High for Executor.
*   **Verdict**: **Avoid**. Too slow/expensive for general chat.

## 3. Quantitative Comparison (Estimated)

| Metric | Current (Keyword) | Proposed (Vector/Hierarchical) | Change |
| :--- | :--- | :--- | :--- |
| **API Requests** | 1 (Chat) | 1 (Chat) | **0% (No Change)** |
| **Latency** | ~5ms (Regex) | ~20ms (Vector Search) | Negligible |
| **Token Load (Base)** | ~400 tokens (All Summaries) | ~100 tokens (Categories only) | **-75%** |
| **Token Load (Active)** | Variable (Brittle matching) | Optimized (Top-3 semantic) | **More Stable** |
| **Accuracy** | Low (Misses synonyms) | High (Semantic understanding) | **Big Win** |

## 4. Conclusion
**No, the proposed hierarchical approach (Variant B) will NOT increase API calls.** 

It shifts the "selector" from dumb Keyword Matching to smart Vector Matching (using the vector we already compute). It actually **saves tokens** by allowing us to hide the full list of summaries and only retrieve what's semantically relevant.
