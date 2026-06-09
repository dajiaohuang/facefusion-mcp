---
name: refine-facefusion-plan
description: Refine plan details for a multi-actor FaceFusion project after role binding. Use when you need to add optional per-shot pipeline operations, build plan.json, review or summarize the draft plan, approve previews, or retry only the affected task instead of rebuilding the project.
---

# Refine Facefusion Plan

Use this skill once cast, shots, and reference decisions are already in place.

## Workflow

1. Read `../../resources/multi-actor-workflow.md`.
2. Ask whether any shot needs optional pipeline operations such as `lip_sync`, `face_enhance`, `frame_enhance`, `background_remove`, `expression_restore`, `face_edit`, `age_modify`, or `frame_colorize`. Default is off.
3. Apply those optional operations with `facefusion_apply_shot_operation_decisions` when needed.
4. Build the preview/final draft with `facefusion_build_multi_actor_plan`.
5. Before any swap execution, call `facefusion_review_multi_actor_configuration` and show the user the full current configuration for confirmation:
   - merged roles and source paths
   - shot ranges and role assignments
   - optional shot operations
   - preview mode and quality profile
   - whether anything is still unresolved
6. In UI mode, render `manifests/plan-view.html` with `facefusion_render_plan_ui`.
7. In no-UI mode, summarize the same confirmation payload in text and wait for explicit approval.
8. Only after explicit user confirmation should you materialize jobs with `facefusion_materialize_multi_actor_jobs`.
9. Use `facefusion_approve_preview` for preview promotion.
10. Use `facefusion_retry_failed_task` for targeted recovery.

## Conversation Rules

- Optional shot pipeline additions are off by default.
- Prefer adding shot operations explicitly instead of implying them from vague quality language.
- Do not rebuild the entire project when only one preview or final task needs a retry.
- Never start swap execution immediately after role/source binding. Always insert one explicit full-configuration confirmation step first.

## Tool Rules

- Use `facefusion_apply_shot_operation_decisions` before plan build when the user asks for shot-level additions.
- Use `facefusion_review_multi_actor_configuration` after plan build and before any materialization or execution.
- Use `facefusion_render_plan_ui` when a visual review is helpful.
- Use `facefusion_approve_preview` instead of editing `plan.json` by hand.
- Use `facefusion_retry_failed_task` for localized failure recovery.

## References

- `../../resources/multi-actor-workflow.md`
- `references/plan-refinement-patterns.md`
