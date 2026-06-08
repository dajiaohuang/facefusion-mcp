# Common Workflows

## Single image face swap

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_swapper`, optional `face_enhancer`
- Default provider: `cuda`
- Good preset: `balanced_face_swap`

## Video face swap

- Readiness: `facefusion_health_check`
- Optional prep: `facefusion_download_models`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_swapper`, optional `face_enhancer`, optional `frame_enhancer`
- Default provider: `cuda`
- Good presets: `fast_preview_swap`, `balanced_face_swap`, `quality_face_swap`

## Batch face swap

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_batch_run`
- Recommended processors: `face_swapper`, optional `face_enhancer`
- Good preset: `balanced_face_swap`

## Background removal

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job` or `facefusion_batch_run`
- Recommended processors: `background_remover`
- Good preset: `background_cutout`

## Face enhancement

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_enhancer`
- Good preset: `portrait_enhance`

## Lip sync

- Readiness: `facefusion_health_check`
- Optional prep: `facefusion_download_models`
- Main tool: `facefusion_run_job`
- Recommended processors: `lip_syncer`
- Good preset: `lip_sync_clean`

## Frame restoration

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `frame_enhancer`
- Good preset: `frame_restore`

## Archive colorization

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `frame_colorizer`, optional `frame_enhancer`
- Good preset: `archive_colorize`

## Face debugging

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_debugger`
- Good preset: `face_debug_overlay`

## Job queue workflow

- Create: `facefusion_create_job`
- Add or edit steps: `facefusion_update_job_steps`
- Inspect queue: `facefusion_manage_jobs`
- Submit or run: `facefusion_run_jobs`
- Retry failures: `facefusion_run_jobs` with retry mode
