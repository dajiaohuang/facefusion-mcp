---
name: draft-facefusion-cast-and-shots
description: Create the initial draft state for a multi-actor FaceFusion project. Use when the user is at the beginning of a multi-role workflow and you need to gather source candidates, build or update cast.json, define shots or time ranges, and produce the first draft state before reference review.
---

# Draft Facefusion Cast And Shots

Use this skill for the first planning pass of a multi-actor project.

## Workflow

1. Start with `../../resources/multi-actor-workflow.md`.
2. If environment readiness is unknown, call `facefusion_health_check`.
3. Build or update source candidates with `facefusion_define_cast`.
4. Build or update shot ranges with `facefusion_plan_shots`.
5. Do not wait for every detail. Once there is enough information for a first draft, produce it.
6. If target roles are still unclear, stop after a valid first draft and hand off to reference review instead of forcing manual labeling too early.

## Conversation Rules

- Ask for source candidate images and target media first.
- Ask for rough time ranges if exact cut points are not ready yet.
- Prefer named roles, bounded time segments, and simple first-pass assumptions.
- If the user gave partial information, create the first valid draft and keep moving.

## Tool Rules

- Use `facefusion_define_cast` for source candidates and role assets.
- Use `facefusion_plan_shots` for shot boundaries and early operation placeholders.
- Leave roles unresolved in a shot when that is cleaner than guessing.
- Do not jump into reference merge, shot-operation refinement, or preview approval from this skill.

## References

- `../../resources/multi-actor-workflow.md`
- `references/draft-patterns.md`
