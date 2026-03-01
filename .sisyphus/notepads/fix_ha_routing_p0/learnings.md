## 2026-03-01: Hardened HomeAssistant Skill Rules

- **Rule 0 Addition**: Added a strict two-step verification process for temperature and state queries. This forces the agent to search for entities before attempting to get their state, preventing 'guessing' of entity IDs which was a primary failure mode.
- **Intent Expansion**: Expanded  to cover more natural language variations of temperature and home control queries, improving the router's ability to trigger the HomeAssistant skill accurately.
- **Verification Pattern**: The two-step process ( -> ) is now the explicitly required pattern for all state-based queries.

## 2026-03-01: Hardened HomeAssistant Skill Rules

- **Rule 0 Addition**: Added a strict two-step verification process for temperature and state queries. This forces the agent to search for entities before attempting to get their state, preventing 'guessing' of entity IDs which was a primary failure mode.
- **Intent Expansion**: Expanded `intent_keywords` to cover more natural language variations of temperature and home control queries, improving the router's ability to trigger the HomeAssistant skill accurately.
- **Verification Pattern**: The two-step process (`list_entities` -> `get_state`) is now the explicitly required pattern for all state-based queries.
