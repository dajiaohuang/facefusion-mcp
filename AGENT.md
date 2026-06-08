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
- `facefusion_render_reference_ui`
- `facefusion_build_multi_actor_plan`
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

Prefer these processor starting points:

- face swap: `face_swapper`
- face cleanup: `face_enhancer`
- lip sync: `lip_syncer`
- cutout: `background_remover`
- frame cleanup: `frame_enhancer`

Plugin runtime overrides:

- `facefusion_run_job`: `misc_options.skip_nsfw_check=true`
- `facefusion_launch_ui`: `misc_options.skip_nsfw_check=true`
- `facefusion_batch_run`: `misc_options.skip_nsfw_check=true`
- `facefusion_run_jobs`: `skip_nsfw_check=true`

This wrapper-based override only affects plugin-launched runs and does not patch the FaceFusion source tree on disk.

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
6. `facefusion_build_multi_actor_plan`
7. `facefusion_render_plan_ui` when the user wants a visual review layer
8. `facefusion_materialize_multi_actor_jobs`
9. `facefusion_approve_preview`
10. `facefusion_retry_failed_task` when needed

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
4. show the discovered clusters and prefills back to the user
5. ask the user which clusters should merge into one final role
6. ask whether each merged role should keep the prefilled source face or switch to another source
7. if any merged role still has no source face, ask the user to send or name the missing target source image
8. call `facefusion_apply_reference_decisions`
9. only then build `plan.json`

What the agent should tell the user after reference discovery:

- how many target face clusters were detected in the original footage
- which shots each cluster appears in
- which source role was prefilled for each cluster, if any
- which clusters look like they should be merged into one final role

What the agent should ask next:

- "Should any of these detected clusters be merged into one role?"
- "For each merged role, keep the prefilled target face or switch to another source face?"
- "Which detected roles still need a source image?"

OpenClaw or remote-image case:

- if the user says they will send source images later, keep the cluster merge decisions first and allow source assignment to remain unresolved temporarily
- once the user sends the missing image, rerun only `facefusion_apply_reference_decisions` with the new source binding instead of rebuilding discovery from scratch
- when summarizing the state, explicitly separate:
  - detected target roles
  - merged final roles
  - assigned source faces
  - still-missing source faces

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
