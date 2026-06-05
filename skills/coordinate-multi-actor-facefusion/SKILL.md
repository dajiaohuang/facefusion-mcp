---
name: coordinate-multi-actor-facefusion
description: Coordinate a conversational multi-actor FaceFusion project through the FaceFusion MCP plugin. Use when the user wants to swap multiple roles or multiple faces across one or more videos, map source faces to named roles, define shot ranges, approve previews before final renders, or retry only the affected shot instead of rerunning the entire project.
---

# Coordinate Multi-Actor Facefusion

Use this skill to run a phased agent workflow for multi-role and multi-face swaps.

## Workflow

1. Start by reading `../../resources/multi-actor-workflow.md`.
2. If environment readiness is unknown, call `facefusion_health_check`.
3. Build or update project cast with `facefusion_define_cast`.
4. Build or update shot ranges with `facefusion_plan_shots`.
5. Generate preview and final tasks with `facefusion_build_multi_actor_plan`.
6. Materialize preview-first work with `facefusion_materialize_multi_actor_jobs`.
7. After preview review, call `facefusion_approve_preview` instead of editing `plan.json` manually.
8. If one preview or render fails, use `facefusion_retry_failed_task` before rebuilding the full project.

## Conversation Rules

- Keep each turn focused on one phase: cast, shots, preview approval, or retry.
- Ask only the minimum blocking question for the current phase.
- Prefer named roles and bounded time ranges over low-level FaceFusion flags.
- Summarize the current project state after every material change so the user can confirm it.
- For unclear long videos, offer a shot-planning pass before trying to render.
- For multi-face same-frame shots, default to preview-first and reference-mode planning.

## Tool Rules

- Stay in the multi-actor tool family unless the user abandons the project workflow.
- Do not jump straight to `facefusion_run_job` for a multi-role project.
- Do not unlock final tasks without `facefusion_approve_preview`.
- Do not rerun the whole queue when one task can be retried locally.
- Use `facefusion_manage_jobs(action="list")` when the user asks what is queued or what already materialized.

## References

- `../../resources/multi-actor-workflow.md`
- `../../resources/parameter-mapping.md`
- `../../resources/processors.md`
- `references/conversation-patterns.md`
