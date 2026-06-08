---
name: coordinate-multi-actor-facefusion
description: Coordinate a conversational multi-actor FaceFusion project through the FaceFusion MCP plugin. Use when the user wants to swap multiple roles or multiple faces across one or more videos, map source faces to named roles, define shot ranges, approve previews before final renders, or retry only the affected shot instead of rerunning the entire project.
---

# Coordinate Multi-Actor Facefusion

Use this skill to run a phased agent workflow for multi-role FaceFusion projects, including swaps, lip sync, enhancement, cutouts, and other shot-level processor combinations.

## Workflow

1. Start by reading `../../resources/multi-actor-workflow.md`.
2. If environment readiness is unknown, call `facefusion_health_check`.
3. Build or update project cast with `facefusion_define_cast`. At this stage the cast may represent source candidates rather than final target-role assignments.
4. Build or update shot ranges with `facefusion_plan_shots`. Roles may stay empty if the project is using reference-first target-role discovery.
5. Run `facefusion_discover_role_references` to sample faces from each shot, cluster target roles across the original footage, and prefill possible source-role matches.
6. If the user wants a visual review layer before planning, render `manifests/reference-view.html` with `facefusion_render_reference_ui`.
7. Ask the user whether any detected target-face clusters should be merged into one final role, and whether the prefilled source face for each merged role should stay or change.
8. Apply those merge and source decisions with `facefusion_apply_reference_decisions`.
9. Generate preview and final tasks with `facefusion_build_multi_actor_plan`.
10. If the user wants a visual review layer, render `manifests/plan-view.html` with `facefusion_render_plan_ui`.
11. Materialize preview-first work with `facefusion_materialize_multi_actor_jobs`.
12. After preview review, call `facefusion_approve_preview` instead of editing `plan.json` manually.
13. If one preview or render fails, use `facefusion_retry_failed_task` before rebuilding the full project.

## Conversation Rules

- Keep each turn focused on one phase: source candidates, shots, reference merge, preview approval, or retry.
- Ask only the minimum blocking question for the current phase.
- Prefer named roles and bounded time ranges over low-level FaceFusion flags.
- For non-swap work, capture the intended shot-level operation explicitly, for example `lip_sync`, `face_enhance`, or `background_remove`.
- Summarize the current project state after every material change so the user can confirm it.
- For unclear long videos, offer a shot-planning pass before trying to render.
- For multi-face same-frame shots, default to preview-first and reference-mode planning.
- When the user is not sure who is who in the target footage, do not force manual role labeling too early. Use reference discovery first, then ask merge and source questions.
- If the agent already knows likely source names from the user's request, pass them into `facefusion_discover_role_references` through `source_hint_names` so the review step can prefill likely matches such as `kobe`, `zxf`, or other named sources.
- If some detected target roles have no prefilled source face, explicitly ask the user which final role each one should become and which source image should be used.
- If the user is working through OpenClaw or another remote image-sending agent, allow source assignment to happen after role clustering. Treat "I will send the face image next" as a valid partial state.

## Tool Rules

- Stay in the multi-actor tool family unless the user abandons the project workflow.
- Do not jump straight to `facefusion_run_job` for a multi-role project.
- Use `facefusion_render_reference_ui` when the user needs to review detected target faces before final role assignment.
- Use `facefusion_render_plan_ui` when the user asks to inspect or present the plan visually.
- Do not unlock final tasks without `facefusion_approve_preview`.
- Do not rerun the whole queue when one task can be retried locally.
- Use `facefusion_manage_jobs(action="list")` when the user asks what is queued or what already materialized.
- When applying reference decisions, prefer changing only the unresolved or incorrect role bindings instead of rebuilding the whole project from scratch.

## References

- `../../resources/multi-actor-workflow.md`
- `../../resources/parameter-mapping.md`
- `../../resources/processors.md`
- `references/conversation-patterns.md`
