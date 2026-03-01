# Nexus Agent: Self-Evolution & Learning Loop

## The "Designer" Architecture
The system employs an offline `MemSkillDesigner` agent to self-heal and improve over time.

1. **Detection**: Scans `MemorySkill` metrics for high `negative_count` or `ROUTING LESSON` entries.
2. **Analysis**: The Designer LLM analyzes recent failure samples.
3. **Evolution**: Generates an improved `prompt_template`.
4. **Canary Testing**: Shadow-tests the new prompt against historical inputs.
5. **Human-in-the-Loop (HITL)**: Saves to `SkillChangelog` for Admin approval via the Cortex Dashboard.
