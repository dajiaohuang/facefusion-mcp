# FaceFusion Commands

## Top-level commands

- `run`: launch the interactive UI workflow
- `headless-run`: execute one processing task without the UI
- `batch-run`: execute a pattern-based batch workflow
- `force-download`: prefetch or repair downloadable model assets
- `benchmark`: compare provider and processor performance
- `job-list`: list jobs by status
- `job-create`: create a drafted job
- `job-submit`: move one drafted job into the queue
- `job-submit-all`: queue every drafted job
- `job-delete`: delete one job
- `job-delete-all`: delete all jobs of eligible statuses
- `job-add-step`: append a step to a drafted job
- `job-remix-step`: clone a prior step into a new drafted step
- `job-insert-step`: insert a step at a specific position
- `job-remove-step`: remove one drafted step
- `job-run`: execute one queued job
- `job-run-all`: execute all queued jobs
- `job-retry`: retry one failed job
- `job-retry-all`: retry all failed jobs

## When to use each command family

- Use `headless-run` for a single direct task with explicit paths.
- Use `batch-run` when source, target, or output inputs are best expressed as file patterns.
- Use `force-download` when the machine is missing models or has corrupt downloads.
- Use `benchmark` when the user cares about speed, provider selection, or memory tradeoffs.
- Use `job-*` commands when the user wants a queue, drafts, retries, or multi-step orchestration.

## MCP mapping

- `facefusion_run_job` -> `headless-run`
- `facefusion_batch_run` -> `batch-run`
- `facefusion_download_models` -> `force-download`
- `facefusion_benchmark` -> `benchmark`
- `facefusion_create_job` -> `job-create`
- `facefusion_update_job_steps` -> `job-add-step`, `job-insert-step`, `job-remix-step`, `job-remove-step`
- `facefusion_run_jobs` -> `job-submit`, `job-submit-all`, `job-run`, `job-run-all`, `job-retry`, `job-retry-all`
- `facefusion_manage_jobs` -> `job-list`, `job-delete`, `job-delete-all`
