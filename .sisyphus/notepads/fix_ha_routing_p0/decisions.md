
## Phase 1 Implementation Decisions
- **Relaxed Threshold**: Lowered `ROUTING_THRESHOLD` from 0.35 to 0.30 in `app/core/config.py`. This allows short Chinese queries (like "查温度") which often have lower vector similarity scores to be correctly routed.
- **Improved Multiplier**: Refactored `_domain_multiplier` in `app/core/tool_router.py` to be less punitive.
  - Added a fallback check for "homeassistant" or "smart_home" in the raw domain string when in "home" context.
  - Changed the default fallback from `cross` (0.7) to `adjacent` (1.0) for tools with missing or ambiguous metadata.
  - Explicitly penalize only when context mismatch is confirmed (e.g., system/admin tools in a home context).
