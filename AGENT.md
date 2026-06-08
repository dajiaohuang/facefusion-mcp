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
- `facefusion_download_models`
- `facefusion_benchmark`

### Direct Execution

- `facefusion_run_job`
- `facefusion_batch_run`

### Job Queue

- `facefusion_create_job`
- `facefusion_update_job_steps`
- `facefusion_run_jobs`
- `facefusion_manage_jobs`

### Multi-Actor Project State

- `facefusion_define_cast`
- `facefusion_plan_shots`
- `facefusion_build_multi_actor_plan`
- `facefusion_materialize_multi_actor_jobs`
- `facefusion_approve_preview`
- `facefusion_retry_failed_task`

## Confirmation Rules

- Always start environment work with `facefusion_health_check`.
- If `needs_install` or `needs_setup` is true, explain the missing components first.
- Never call `facefusion_install_or_setup` until the user explicitly confirms installation or setup.
- Do not overwrite existing outputs unless the user clearly wants replacement.
- Do not delete queued jobs without clear user intent.

## Install Path Rules

When the user confirms setup, `facefusion_install_or_setup` chooses the install root in this order:

1. explicit `install_root`
2. `FACEFUSION_ROOT`
3. an already detected FaceFusion checkout
4. `plugins/facefusion-local/.facefusion-runtime`

The virtual environment lives inside the chosen root at `.venv`.

## Direct Task Routing

Use `facefusion_run_job` when the user gives one explicit set of source and target paths.

Use `facefusion_batch_run` when the user clearly wants pattern-based or directory-scale processing.

Prefer these processor starting points:

- face swap: `face_swapper`
- face cleanup: `face_enhancer`
- lip sync: `lip_syncer`
- cutout: `background_remover`
- frame cleanup: `frame_enhancer`

## Multi-Actor Workflow

For multi-role projects, do not jump straight to a one-off run.

Use this order:

1. `facefusion_define_cast`
2. `facefusion_plan_shots`
3. `facefusion_build_multi_actor_plan`
4. `facefusion_materialize_multi_actor_jobs`
5. `facefusion_approve_preview`
6. `facefusion_retry_failed_task` when needed

Treat the project as three persisted layers:

- `cast.json`
- `shots.json`
- `plan.json`

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
