---
name: coordinate-multi-actor-facefusion
description: Coordinate a conversational multi-actor FaceFusion project through the FaceFusion MCP plugin. Use when the user wants to swap multiple roles or multiple faces across one or more videos, map source faces to named roles, define shot ranges, approve previews before final renders, or retry only the affected shot instead of rerunning the entire project.
---

# Coordinate Multi-Actor Facefusion

Use this skill to run a phased agent workflow for multi-role FaceFusion projects, including swaps, lip sync, enhancement, cutouts, and other shot-level processor combinations.

## Workflow

1. Start by reading `../../resources/multi-actor-workflow.md`.
2. If environment readiness is unknown, call `facefusion_health_check`.
3. Check `default_ui_mode` from the plugin environment. Treat UI review as the default when it is enabled, but do not block on it.
4. Build or update project cast with `facefusion_define_cast`. At this stage the cast may represent source candidates rather than final target-role assignments.
5. Build or update shot ranges with `facefusion_plan_shots`. Roles may stay empty if the project is using reference-first target-role discovery.
6. Run `facefusion_discover_role_references` to sample faces from each shot, cluster target roles across the original footage, and prefill possible source-role matches.
7. After the first prompt, do not wait for every detail. Produce the initial draft state first. In UI mode this usually means rendering `manifests/reference-view.html` with `facefusion_render_reference_ui`; in no-UI mode it means summarizing the current cast and reference draft in chat.
8. Ask the user whether any detected target-face clusters should be merged into one final role, and whether the prefilled source face for each merged role should stay or change.
9. Apply those merge and source decisions with `facefusion_apply_reference_decisions`.
10. Ask whether any shot also needs optional pipeline operations such as lip sync, face enhancement, frame enhancement, background removal, expression restore, face edit, age modify, or colorization. Default is off.
11. Apply those shot-level optional operations with `facefusion_apply_shot_operation_decisions`.
12. Generate preview and final tasks with `facefusion_build_multi_actor_plan`.
13. In UI mode, render `manifests/plan-view.html` with `facefusion_render_plan_ui`. In no-UI mode, summarize the plan draft in chat and keep filling gaps conversationally.
14. Materialize preview-first work with `facefusion_materialize_multi_actor_jobs`.
15. After preview review, call `facefusion_approve_preview` instead of editing `plan.json` manually.
16. If one preview or render fails, use `facefusion_retry_failed_task` before rebuilding the full project.

## Conversation Rules

- Keep each turn focused on one phase: source candidates, shots, reference merge, preview approval, or retry.
- Ask only the minimum blocking question for the current phase.
- Prefer named roles and bounded time ranges over low-level FaceFusion flags.
- For non-swap work, capture the intended shot-level operation explicitly, for example `lip_sync`, `face_enhance`, or `background_remove`.
- Optional per-shot pipeline additions are off by default. Ask before adding them broadly across all shots.
- Summarize the current project state after every material change so the user can confirm it.
- For unclear long videos, offer a shot-planning pass before trying to render.
- For multi-face same-frame shots, default to preview-first and reference-mode planning.
- When the user is not sure who is who in the target footage, do not force manual role labeling too early. Use reference discovery first, then ask merge and source questions.
- In both UI and no-UI mode, generate an initial draft after the first prompt rather than waiting for every detail up front.
- If `default_ui_mode=true`, prefer the HTML review layer by default.
- If `default_ui_mode=false`, keep the whole refinement loop inside the agent conversation while still generating the same draft artifacts under the hood.
- If the agent already knows likely source names from the user's request, pass them into `facefusion_discover_role_references` through `source_hint_names` so the review step can prefill likely matches such as `kobe`, `zxf`, or other named sources.
- If some detected target roles have no prefilled source face, explicitly ask the user which final role each one should become and which source image should be used.
- If the user is working through OpenClaw or another remote image-sending agent, allow source assignment to happen after role clustering. Treat "I will send the face image next" as a valid partial state.

## Tool Rules

- Stay in the multi-actor tool family unless the user abandons the project workflow.
- Do not jump straight to `facefusion_run_job` for a multi-role project.
- Use `facefusion_render_reference_ui` when the user needs to review detected target faces before final role assignment.
- Use `facefusion_apply_shot_operation_decisions` when the user wants to add lip sync, face repair, frame enhancement, background removal, or similar optional operations across all shots or selected shot ids before plan build.
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
