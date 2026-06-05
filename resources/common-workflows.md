# Common Workflows

## Single image face swap

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_swapper`, optional `face_enhancer`
- Default provider: `cuda`

## Video face swap

- Readiness: `facefusion_health_check`
- Optional prep: `facefusion_download_models`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_swapper`, optional `face_enhancer`, optional `frame_enhancer`
- Default provider: `cuda`

## Batch face swap

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_batch_run`
- Recommended processors: `face_swapper`, optional `face_enhancer`

## Background removal

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job` or `facefusion_batch_run`
- Recommended processors: `background_remover`

## Face enhancement

- Readiness: `facefusion_health_check`
- Main tool: `facefusion_run_job`
- Recommended processors: `face_enhancer`

## Lip sync

- Readiness: `facefusion_health_check`
- Optional prep: `facefusion_download_models`
- Main tool: `facefusion_run_job`
- Recommended processors: `lip_syncer`

## Job queue workflow

- Create: `facefusion_create_job`
- Add or edit steps: `facefusion_update_job_steps`
- Inspect queue: `facefusion_manage_jobs`
- Submit or run: `facefusion_run_jobs`
- Retry failures: `facefusion_run_jobs` with retry mode
