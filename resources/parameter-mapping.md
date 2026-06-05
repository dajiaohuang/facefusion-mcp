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

### Face and processor options
- Any `snake_case` option under `face_options` is forwarded as a flag using the same conversion rule.
- This is how processor-specific settings like `face_swapper_model` or `background_remover_model` are passed.

## Tool-specific required fields

- `facefusion_run_job`: `source_paths`, `target_path`, `output_path`
- `facefusion_batch_run`: `source_pattern`, `target_pattern`, `output_pattern`
- `facefusion_create_job`: `job_id`
- `facefusion_update_job_steps`: `action`, `job_id`, and sometimes `step_index`
- `facefusion_run_jobs`: `mode`, and `job_id` for single-job modes

## `extra_args`

- `extra_args[]` appends raw flags after structured argument generation.
- Use it only for advanced or newly added CLI flags that are not yet modeled.
- Do not use `extra_args` to override required-path validation or overwrite checks.
