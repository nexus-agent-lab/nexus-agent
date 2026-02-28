## 2026-02-28 - Update priorities.md with Quantization Safety Epics

**Decision:**
Added two new Epics to `docs/priorities.md` as part of the Phase 2 of `quantization_safety_hardening.md`.

**Content Added:**
1. **Epic 1: Aggressive Tool Output Compaction (DualPath inspired) [P1]**
   - Focuses on summarization of tool outputs to save KV-Cache and reduce hallucination risk in quantized models.
2. **Epic 2: Quantization-Aware Safety Benchmark (T-PTQ inspired) [P2]**
   - Focuses on building a test suite to evaluate safety and alignment under quantization.

**Rationale:**
These epics were added to the project roadmap to track long-term architectural solutions for safety issues specific to local quantized models.
