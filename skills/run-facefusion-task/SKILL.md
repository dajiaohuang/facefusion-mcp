---
name: run-facefusion-task
description: Execute direct local FaceFusion processing tasks through the FaceFusion Local MCP plugin. Use when the user asks to swap faces, enhance faces, remove backgrounds, lip-sync audio, colorize frames, or run a one-off or batch media transformation on local image, audio, or video files.
---

# Run Facefusion Task

Use this skill to turn a normal FaceFusion media-processing request into the right MCP tool calls.

## Workflow

1. Determine whether the user wants a one-off task or a batch workflow.
2. If readiness is unknown, call `facefusion_health_check`.
3. Read `../../resources/processors.md` and `../../resources/common-workflows.md` when you need processor or workflow guidance.
4. If the task is missing assets or looks like a first run, call `facefusion_download_models`.
5. Use `facefusion_run_job` for one explicit set of paths.
6. Use `facefusion_batch_run` for pattern-based work.

## Tool Rules

- Prefer `facefusion_run_job` for direct source and target paths.
- Prefer `facefusion_batch_run` only when the request is clearly pattern-based or directory-scale.
- Do not use job-management tools unless the user explicitly asks for drafts, queues, retries, or multi-step orchestration.
- Respect the MCP overwrite guard. If the output path already exists, choose a new output path or set `overwrite=true` only when the user clearly intends replacement.

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
