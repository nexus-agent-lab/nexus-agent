# Active Task Index

## Goal
Keep advancing the active P0-2 auth/ingress thread while also capturing architecture decisions that shape the skill, worker, and learning stack.

## Current State
- Bearer JWT migration for web/backend is complete.
- User independently fixed and committed the nginx DNS rediscovery issue.
- The Project Context tree had been partially incomplete; `index.md` has now been restored.
- A new architecture note now exists at `docs/architecture/autoskill_self_evolution_integration.md` describing how to adapt AutoSkill-style experience-driven skill evolution to this repository.
- These documentation/context updates were committed on `2026-03-23` as `d4be5d0`.
- A new estimate note now exists at `docs/architecture/p0_entry_binding_loop_estimate.md` covering the recommended next product slice.
- A new implementation plan now exists at `docs/architecture/p0_entry_binding_loop_implementation_plan.md`.
- A new WeChat channel plan now exists at `docs/architecture/wechat_channel_integration_plan.md`, based on the local `vendor/weixin-ClawBot-API` reference project.
- The local pre-commit path now uses `scripts/check.sh` as a staged-only gate for Python lint, staged web ESLint, and inferred related pytest targets instead of running repo-wide checks on every commit.
- Milestone 1 of the Telegram/web entry-loop plan is now partially implemented: shared derived identity-access state plus clearer Telegram/web onboarding and handoff messaging.
- Milestone 2 has also started: Telegram bind outcomes and handoff status payloads now use shared structured helpers instead of duplicating branch-specific message mapping.

## Recent Decision
- Treat AutoSkill-inspired learning as a typed patch pipeline rather than a single "append rule" action.
- Keep `MemSkillDesigner` focused on memory prompts.
- Introduce a future `SkillEvolutionEngine` for skill-card, routing-hint, and policy evolution.

## Next Action
If continuing product work, keep moving through Milestone 2 from `docs/architecture/p0_entry_binding_loop_implementation_plan.md` (bind-flow simplification and shared outcome shapes), then move to the WeChat transport spike. If focusing on developer workflow, validate the new staged-only hook behavior against representative Python and `web/` changes before broadening or tightening the affected-test heuristic.
