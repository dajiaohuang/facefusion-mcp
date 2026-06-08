---
name: run-facefusion-task
description: Execute direct local FaceFusion processing tasks through the FaceFusion Local MCP plugin. Use when the user asks to swap faces, enhance faces, remove backgrounds, lip-sync audio, colorize frames, or run a one-off or batch media transformation on local image, audio, or video files.
---

# Run Facefusion Task

Use this skill to turn a normal FaceFusion media-processing request into the right MCP tool calls.

## Workflow

1. Determine whether the user wants a one-off headless task, an interactive UI session, or a batch workflow.
2. If readiness is unknown, call `facefusion_health_check`.
3. Read `../../resources/processors.md` and `../../resources/common-workflows.md` when you need processor or workflow guidance.
4. If the user asks what options or models exist, call `facefusion_list_capabilities`.
5. If the user wants a quick starting point, call `facefusion_list_presets` and choose a matching preset.
6. If the task is missing assets or looks like a first run, call `facefusion_download_models`.
7. Use the matching `facefusion_task_*` shortcut whenever the request maps cleanly to a named task.
8. Use `facefusion_launch_ui` when the user wants FaceFusion head mode, wants to interactively tweak settings, or asks for browser/UI workflows.
9. Use `facefusion_run_job` only when no task shortcut fits well and the user is effectively describing a raw headless run.
10. Use `facefusion_batch_run` for pattern-based work.

## Tool Rules

- Prefer `facefusion_task_*` tools over `facefusion_run_job` for normal user tasks.
- Prefer `facefusion_launch_ui` when the user explicitly asks for the UI or wants a visible interactive session.
- Prefer `facefusion_batch_run` only when the request is clearly pattern-based or directory-scale.
- Prefer a matching built-in `preset` before hand-authoring many low-level options when the task is standard.
- Do not use job-management tools unless the user explicitly asks for drafts, queues, retries, or multi-step orchestration.
- Respect the MCP overwrite guard. If the output path already exists, choose a new output path or set `overwrite=true` only when the user clearly intends replacement.
- Use `misc_options.skip_nsfw_check=true` only when the user explicitly asks to bypass FaceFusion NSFW detection.

## Defaults

- Default execution provider: `cuda`, with fallback to `cpu`
- Default log level: `info`
- Common starting processors:
  - face swap: `face_swapper`
  - face cleanup: `face_enhancer`
  - cutout: `background_remover`
  - lip sync: `lip_syncer`

## References

- `../../resources/parameter-mapping.md`
- `../../resources/processors.md`
- `../../resources/common-workflows.md`
