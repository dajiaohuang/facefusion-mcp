# FaceFusion MCP Agent Guide

This repository exposes FaceFusion through MCP tools, resources, and prompts.

Use this guide when operating as an agent against the local plugin.

## Primary Goals

- Prepare and validate a local FaceFusion environment.
- Run direct FaceFusion media-processing tasks.
- Coordinate multi-actor and multi-face projects through stored project state.
- Keep risky work preview-first and retry only the affected shot or task.

## Core Tool Families

### Environment

- `facefusion_health_check`
- `facefusion_install_or_setup`
- `facefusion_list_capabilities`
- `facefusion_list_presets`
- `facefusion_check_queue`
- `facefusion_download_models`
- `facefusion_benchmark`

### Direct Execution

- `facefusion_task_face_swap`
- `facefusion_task_lip_sync`
- `facefusion_task_remove_background`
- `facefusion_task_enhance_face`
- `facefusion_task_enhance_frame`
- `facefusion_task_colorize_frames`
- `facefusion_task_edit_face`
- `facefusion_task_restore_expression`
- `facefusion_task_modify_age`
- `facefusion_task_debug_faces`
- `facefusion_run_job`
- `facefusion_launch_ui`
- `facefusion_batch_run`

### Job Queue

- `facefusion_create_job`
- `facefusion_update_job_steps`
- `facefusion_run_jobs`
- `facefusion_manage_jobs`

### Multi-Actor Project State

- `facefusion_define_cast`
- `facefusion_plan_shots`
- `facefusion_discover_role_references`
- `facefusion_apply_reference_decisions`
- `facefusion_apply_shot_operation_decisions`
- `facefusion_render_reference_ui`
- `facefusion_build_multi_actor_plan`
- `facefusion_review_multi_actor_configuration`
- `facefusion_render_plan_ui`
- `facefusion_materialize_multi_actor_jobs`
- `facefusion_approve_preview`
- `facefusion_retry_failed_task`

## Confirmation Rules

- Always start environment work with `facefusion_health_check`.
- If `needs_install` or `needs_setup` is true, explain the missing components first.
- Never call `facefusion_install_or_setup` until the user explicitly confirms installation or setup.
- Do not overwrite existing outputs unless the user clearly wants replacement.
- Do not delete queued jobs without clear user intent.
- Use `skip_nsfw_check` only when the user explicitly asks to bypass FaceFusion NSFW detection.

## Install Path Rules

When the user confirms setup, `facefusion_install_or_setup` chooses the install root in this order:

1. explicit `install_root`
2. `FACEFUSION_ROOT`
3. an already detected FaceFusion checkout
4. `plugins/facefusion-local/.facefusion-runtime`

The virtual environment lives inside the chosen root at `.venv`.

After a successful plugin-managed install or setup, persist:

- `facefusion_root`
- `python_path`

to `facefusion.env.json` in the plugin root so later runs can resolve the same environment without relying on autodetection.

## Direct Task Routing

Prefer the `facefusion_task_*` tools for normal user requests such as face swap, lip sync, background removal, face enhancement, frame enhancement, colorization, face editing, expression restoration, age modification, or debugging overlays.

Use `facefusion_run_job` when the user gives one explicit set of source and target paths and the task shortcut layer is not a clean fit.

Use `facefusion_launch_ui` when the user wants FaceFusion's head mode, wants to inspect or tweak the workflow interactively, or asks for UI-specific layouts or workflows.

Use `facefusion_batch_run` when the user clearly wants pattern-based or directory-scale processing.

Use `facefusion_list_capabilities` when the user asks what FaceFusion can do on this machine, including model choices, UI layouts, face-detection options, masking options, or benchmark ranges.

Use `facefusion_list_presets` when the user wants a fast starting point rather than building all run options manually.

Use `facefusion_check_queue` when the user asks whether the background worker is alive, how many jobs remain, or whether recent queued work is still pending.

Normal task defaults should come from `facefusion.env.json`, especially:

- `default_ui_mode`
- `task_defaults.common`
- `task_defaults.<task_kind>`
- `tool_defaults.common`
- `tool_defaults.<tool_name>`

Only pass explicit `preset` or low-level options when the user wants to override those environment defaults.

Interaction mode rule:

- if `default_ui_mode=true`, prefer generating initial draft state and rendering the relevant review UI early
- if `default_ui_mode=false`, still generate the same initial draft state, but keep refining it through conversation alone
- in both modes, do not wait for every detail before producing the first cast/reference/shot/plan draft

Plugin runtime overrides:

- `facefusion_run_job`: `misc_options.skip_nsfw_check=true`
- `facefusion_launch_ui`: `misc_options.skip_nsfw_check=true`
- `facefusion_batch_run`: `misc_options.skip_nsfw_check=true`
- `facefusion_run_jobs`: `skip_nsfw_check=true`

This wrapper-based override only affects plugin-launched runs and does not patch the FaceFusion source tree on disk. If `facefusion.env.json` already sets `default_skip_nsfw_check`, treat that as the normal baseline and use explicit tool flags only when intentionally overriding it.

## Preset Rule

The following tools accept `preset`:

- `facefusion_run_job`
- `facefusion_launch_ui`
- `facefusion_batch_run`
- `facefusion_benchmark`

Preset defaults are MCP-side bundles. Explicit request fields override them.

## Multi-Actor Workflow

For multi-role projects, do not jump straight to a one-off run.

Use this order:

1. `facefusion_define_cast`
2. `facefusion_plan_shots`
3. `facefusion_discover_role_references`
4. `facefusion_render_reference_ui` when the user wants a visual review layer before role merge
5. `facefusion_apply_reference_decisions`
6. `facefusion_apply_shot_operation_decisions` when the user wants optional per-shot pipeline additions such as lip sync, face repair, frame enhancement, background removal, or other non-default operations
7. `facefusion_build_multi_actor_plan`
8. `facefusion_review_multi_actor_configuration`
9. `facefusion_render_plan_ui` when the user wants a visual review layer
10. Wait for explicit user confirmation of the full configuration
11. `facefusion_materialize_multi_actor_jobs`
12. `facefusion_approve_preview`
13. `facefusion_retry_failed_task` when needed

Treat the project as three persisted layers:

- `cast.json`
- `shots.json`
- `plan.json`

Reference-first planning adds one more persisted layer before final plan materialization:

- `references.json`

The optional UI review artifact lives alongside them in:

- `manifests/reference-view.html`
- `manifests/plan-view.html`

## Reference-First Role Discovery

Use a reference-first flow when the user does not want to label every target role manually up front, when the video has repeated characters across many shots, or when the user may send source face images later from another agent session such as OpenClaw.

Recommended order:

1. create source candidates in `cast.json`
2. split the target video into `shots.json`
3. run `facefusion_discover_role_references`
4. show the discovered clusters and prefills back to the user, either in the review UI or in conversation depending on `default_ui_mode`
5. ask the user which clusters should merge into one final role
6. ask whether each merged role should keep the prefilled source face or switch to another source
7. if any merged role still has no source face, ask the user to send or name the missing target source image
8. call `facefusion_apply_reference_decisions`
9. ask whether any shot also needs optional pipeline operations such as `lip_sync`, `face_enhance`, `frame_enhance`, `background_remove`, `expression_restore`, `face_edit`, `age_modify`, or `frame_colorize`
10. if yes, call `facefusion_apply_shot_operation_decisions`
11. only then build `plan.json`
12. call `facefusion_review_multi_actor_configuration` and return the full settings for confirmation
13. only after explicit confirmation may you materialize or run swap jobs

UI-mode default:

- if `default_ui_mode=true`, the initial conversational pass should normally produce draft `cast.json`, `references.json`, `shots.json`, and then render `reference-view.html`
- after the user refines merge/source/shot-operation choices, build `plan.json` and render `plan-view.html`
- continue asking follow-up questions until all missing details are filled, even when the UI is available

No-UI default:

- if `default_ui_mode=false`, still create the initial draft state after the first prompt
- summarize the draft cast, references, optional shot operations, and plan in chat
- keep asking follow-up questions and applying updates until the plan is fully specified without relying on the HTML review pages

What the agent should tell the user after reference discovery:

- how many target face clusters were detected in the original footage
- which shots each cluster appears in
- which source role was prefilled for each cluster, if any
- which clusters look like they should be merged into one final role

What the agent should ask next:

- "Should any of these detected clusters be merged into one role?"
- "For each merged role, keep the prefilled target face or switch to another source face?"
- "Which detected roles still need a source image?"

What the agent should ask before execution:

- "Here is the full configuration I am about to run. Do you confirm these merge decisions, source images, shot ranges, optional operations, preview settings, and final quality settings?"
- "Should I proceed to preview generation now?"

OpenClaw or remote-image case:

- if the user says they will send source images later, keep the cluster merge decisions first and allow source assignment to remain unresolved temporarily
- once the user sends the missing image, rerun only `facefusion_apply_reference_decisions` with the new source binding instead of rebuilding discovery from scratch
- when summarizing the state, explicitly separate:
  - detected target roles
  - merged final roles
  - assigned source faces
  - still-missing source faces

## Shot-Level Optional Operations

Optional shot pipeline operations are off by default. Treat them as an explicit layer added after role mapping and before plan build.

Examples:

- `lip_sync`
- `face_enhance`
- `frame_enhance`
- `background_remove`
- `expression_restore`
- `face_edit`
- `age_modify`
- `frame_colorize`

What the agent should ask:

- "Should any shot also get lip sync, face repair, frame enhancement, background removal, or other optional pipeline steps?"
- "Apply those to all shots, or only selected shot ids?"

When the user says something like:

- "give every shot face repair"
- "also do lip sync on each shot"
- "add frame enhance to these three shots"

use `facefusion_apply_shot_operation_decisions` before building the final plan.

## Pre-Execution Confirmation Gate

Before any preview or final face-swap execution, always insert one explicit confirmation gate.

Use `facefusion_review_multi_actor_configuration` to return:

- current merged roles
- source paths bound to each role
- shot ranges and role assignments
- per-shot optional operations
- preview mode and quality profile
- any unresolved items that still block execution

Rules:

- Do not go straight from source assignment to `facefusion_materialize_multi_actor_jobs`.
- Do not assume that user-provided source images imply approval to run.
- Treat "use this source for that role" as configuration input, not execution approval.
- Wait for a clear confirmation such as "confirm", "run preview", or "proceed".

## Multi-Actor Operation Model

Shots can contain explicit `operations[]`. Use this when the user wants more than face swap.

Supported high-level operation types:

- `face_swap`
- `lip_sync`
- `face_enhance`
- `background_remove`
- `frame_enhance`
- `frame_colorize`
- `expression_restore`
- `face_edit`
- `age_modify`

Operation rules:

- `face_swap` uses role face assets and supports multi-role reference planning.
- `lip_sync` uses role audio assets and should usually stay one speaking role per task.
- `background_remove`, `frame_enhance`, and `frame_colorize` can run without source assets.
- If different operations need different source asset kinds, split them into separate tasks.

## Preview And Retry Policy

- Multi-role same-frame work should default to preview-first.
- Final tasks should stay blocked until the matching preview is approved.
- Approve previews with `facefusion_approve_preview` instead of manually editing `plan.json`.
- Retry only the affected task with `facefusion_retry_failed_task` before rebuilding a whole project.

## References

Read these only when needed:

- `resources/processors.md`
- `resources/common-workflows.md`
- `resources/troubleshooting.md`
- `resources/multi-actor-workflow.md`
- `skills/coordinate-multi-actor-facefusion/references/conversation-patterns.md`
