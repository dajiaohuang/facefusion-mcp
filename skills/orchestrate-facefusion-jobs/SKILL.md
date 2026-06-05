---
name: orchestrate-facefusion-jobs
description: Build, modify, and operate queued FaceFusion job workflows through the FaceFusion Local MCP plugin. Use when the user asks for drafted jobs, multi-step queues, retries, batch orchestration, or step-wise management instead of a single immediate run.
---

# Orchestrate Facefusion Jobs

Use this skill when the user needs queue-style job management instead of a one-off run.

## Workflow

1. Create a draft with `facefusion_create_job`.
2. Add, insert, remix, or remove steps with `facefusion_update_job_steps`.
3. Inspect queue state with `facefusion_manage_jobs`.
4. Submit, run, or retry with `facefusion_run_jobs`.

## Tool Rules

- Stay in the job tool family for this skill. Do not replace it with direct `facefusion_run_job` unless the user abandons the queue workflow.
- Use `facefusion_manage_jobs(action="list")` to show state before destructive deletes.
- Require clear intent before calling delete actions.

## References

- `../../resources/commands.md`
- `../../resources/common-workflows.md`
- `../../resources/parameter-mapping.md`
- `references/multi-actor-workflow.md`
