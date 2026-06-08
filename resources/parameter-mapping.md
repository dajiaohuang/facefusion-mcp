# MCP Parameter Mapping

## Naming rule

- MCP request fields use `snake_case`.
- CLI flags are derived by replacing underscores with hyphens and prefixing `--`.
- Example: `execution_thread_count` -> `--execution-thread-count`

## Shared request groups

### Execution
- `providers[]` -> `--execution-providers`
- `device_ids[]` -> `--execution-device-ids`
- `thread_count` -> `--execution-thread-count`

### Output options
- `image_quality` -> `--output-image-quality`
- `image_scale` -> `--output-image-scale`
- `audio_encoder` -> `--output-audio-encoder`
- `audio_quality` -> `--output-audio-quality`
- `audio_volume` -> `--output-audio-volume`
- `video_encoder` -> `--output-video-encoder`
- `video_preset` -> `--output-video-preset`
- `video_quality` -> `--output-video-quality`
- `video_scale` -> `--output-video-scale`
- `video_fps` -> `--output-video-fps`
- `overwrite` is an MCP-only guard and is not forwarded to FaceFusion

### Memory options
- `video_memory_strategy` -> `--video-memory-strategy`
- `system_memory_limit` -> `--system-memory-limit`

### Download options
- `download_providers[]` -> `--download-providers`

### Misc options
- `log_level` -> `--log-level`
- `halt_on_error` -> `--halt-on-error`
- `skip_nsfw_check` is plugin-only and is not forwarded to FaceFusion as a CLI flag. The plugin uses it to launch FaceFusion through a wrapper that disables `content_analyser` for that run.

### Face and processor options
- Any `snake_case` option under `face_options` is forwarded as a flag using the same conversion rule.
- This is how processor-specific settings like `face_swapper_model` or `background_remover_model` are passed.

## Tool-specific required fields

- Task shortcuts:
  - `facefusion_task_face_swap`: `source_paths`, `target_path`, `output_path`
  - `facefusion_task_lip_sync`: `source_audio_paths`, `target_path`, `output_path`
  - `facefusion_task_remove_background`: `target_path`, `output_path`
  - `facefusion_task_enhance_face`: `target_path`, `output_path`
  - `facefusion_task_enhance_frame`: `target_path`, `output_path`
  - `facefusion_task_colorize_frames`: `target_path`, `output_path`
  - `facefusion_task_edit_face`: `target_path`, `output_path`
  - `facefusion_task_restore_expression`: `target_path`, `output_path`
  - `facefusion_task_modify_age`: `target_path`, `output_path`
  - `facefusion_task_debug_faces`: `target_path`, `output_path`
- `facefusion_run_job`: `source_paths`, `target_path`, `output_path`
- `facefusion_run_job` also accepts optional `preset`
- `facefusion_launch_ui`: no required media fields; accepts optional `source_paths`, `target_path`, `output_path`, `open_browser`, `ui_layouts[]`, `ui_workflow`, and `dry_run`
- `facefusion_launch_ui` also accepts optional `preset`
- `facefusion_batch_run`: `source_pattern`, `target_pattern`, `output_pattern`
- `facefusion_batch_run` also accepts optional `preset`
- `facefusion_benchmark` also accepts optional `preset`
- `facefusion_create_job`: `job_id`
- `facefusion_update_job_steps`: `action`, `job_id`, and sometimes `step_index`
- `facefusion_run_jobs`: `mode`, and `job_id` for single-job modes
- `facefusion_run_jobs` also accepts plugin-level `skip_nsfw_check`
- `facefusion_render_plan_ui`: `project_id`, with optional `output_path`

## Capability discovery

- `facefusion_list_capabilities(category="all")` exposes:
  - commands
  - processors
  - providers
  - encoders
  - UI layouts and workflows
  - download choices
  - memory and benchmark ranges
  - face option enums and ranges
  - processor-specific model choices
  - presets
- `facefusion_list_presets()` returns the built-in MCP preset library.

## Presets

- Presets are MCP-side default bundles layered over the normal request groups.
- `facefusion.env.json` can inject `tool_defaults.*` and `task_defaults.*` between preset defaults and explicit per-call overrides.
- `facefusion.env.json` can also set `default_ui_mode` to control whether the agent should prefer the HTML review flow by default during multi-step planning.
- Explicit request fields override preset defaults.
- See `facefusion://reference/presets` for the curated preset set.

## `extra_args`

- `extra_args[]` appends raw flags after structured argument generation.
- Use it only for advanced or newly added CLI flags that are not yet modeled.
- Do not use `extra_args` to override required-path validation or overwrite checks.
