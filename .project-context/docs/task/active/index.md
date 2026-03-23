# Active Task Index

## Goal
Keep advancing the active P0-2 auth/ingress thread while also capturing architecture decisions that shape the skill, worker, and learning stack.

## Current State
- Bearer JWT migration for web/backend is complete.
- User independently fixed and committed the nginx DNS rediscovery issue.
- The Project Context tree was partially incomplete before this session; `index.md` did not exist.
- A new architecture note now exists at `docs/architecture/autoskill_self_evolution_integration.md` describing how to adapt AutoSkill-style experience-driven skill evolution to this repository.

## Recent Decision
- Treat AutoSkill-inspired learning as a typed patch pipeline rather than a single "append rule" action.
- Keep `MemSkillDesigner` focused on memory prompts.
- Introduce a future `SkillEvolutionEngine` for skill-card, routing-hint, and policy evolution.

## Next Action
If work resumes on learning/self-evolution, start with `SkillLessonCandidate` aggregation and manual `append_rule` patch generation on existing skill cards before attempting autonomous routing or prompt rewrites.
