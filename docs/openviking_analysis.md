# OpenViking Architecture Analysis

## Overview
OpenViking is a "Context Database" that replaces flat vector storage with a **Filesystem Paradigm** (`viking://`). It organizes data (memories, skills, resources) into a hierarchical directory structure, enabling "Recursive Retrieval" that mimics how humans navigate folders.

## Key Concepts

### 1. Filesystem Paradigm (Virtual FS)
- **Structure**: Everything is a file or directory.
- **URI**: Standardized access via `viking://agent/memories/preferences/...`.
- **Benefit**: Preserves semantic relationships. A "coding" directory provides implicit context to all skills inside it.

### 2. Tiered Context Loading (L0/L1/L2)
Data is stored/accessed in three layers to optimize token usage:
- **L0 (Abstract, ~100 tokens)**: Ultra-short summary. Used for high-speed scanning and relevance filtering.
- **L1 (Overview, ~2000 tokens)**: Detailed summary. Loaded when a node is a "candidate".
- **L2 (Content, Full)**: Original content. Loaded only for the final Top-K results.

**Implementation**: The `VikingFS` abstraction handles transparent fetching of L0/L1/L2 layers based on retrieval stage.

### 3. Recursive Retrieval Algorithm
Implements a **Best-First Search** over the semantic tree:
1.  **Global Search**: First, standard vector search finds "entry points" (deep nodes or relevant directories) to avoid starting only at root.
2.  **Priority Queue**: Candidates are ranked by score.
3.  **Drill Down**: 
    - Pop best candidate.
    - If Directory: Search its children (scoped vector search). Propagate score (Child Score * Alpha + Parent Score).
    - If File: Add to results.
4.  **Convergence**: Stop when Top-K results stabilize.

## Relevance to Nexus Agent

### High Relevance (Adopt Now)
- **L0/L1 Strategy for Memory**: Our current `Memory` system reads full content. We should add an `abstract` column (L0) for the `tool_router` / `memory_retriever` to scan quickly before loading full memory.
- **Hierarchical Skills**: As we add more tools, grouping them (e.g., `homeassistant/light`, `coding/python`) and using a 2-step retrieval (Router -> Sub-Router) will improve accuracy.

### Medium Relevance (Future)
- **Virtual FS**: Implementing a full `viking://` protocol might be overkill roughly *now*, but adopting the *interface* (getting resources by path) is good design.

## Conclusion
OpenViking's "Recursive Retrieval" is effectively a **Semantic Tree Search**. It is superior to flat RAG for large, structured knowledge bases. We should mimic its **Tiered Loading** immediately to optimize our token costs.
