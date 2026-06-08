---
name: orchestrate-facefusion-jobs
description: Build, modify, and operate queued FaceFusion job workflows through the FaceFusion Local MCP plugin. Use when the user asks for drafted jobs, multi-step queues, retries, batch orchestration, or step-wise management instead of a single immediate run.
---

# Orchestrate Facefusion Jobs

Use this skill when the user needs queue-style job management instead of a one-off run.

## Workflow

1. For multi-actor projects, define cast with `facefusion_define_cast`.
2. Build shots with `facefusion_plan_shots`.
3. Build preview/final task plans with `facefusion_build_multi_actor_plan`.
4. Materialize jobs with `facefusion_materialize_multi_actor_jobs`.
5. Approve or reject previews with `facefusion_approve_preview`.
6. Retry only the affected failed task with `facefusion_retry_failed_task`.
7. For lower-level manual workflows, create a draft with `facefusion_create_job`.
8. Add, insert, remix, or remove steps with `facefusion_update_job_steps`.
9. Inspect queue state with `facefusion_manage_jobs`.
10. Submit, run, or retry with `facefusion_run_jobs`.

## Tool Rules

- Stay in the job tool family for this skill. Do not replace it with direct `facefusion_run_job` unless the user abandons the queue workflow.
- Prefer the multi-actor project tools when the user describes roles, shots, or preview-approval loops.
- Use `facefusion_approve_preview` to promote final tasks instead of directly editing project files.
- Use `facefusion_retry_failed_task` for local recovery before rebuilding an entire project plan.
- Use `facefusion_manage_jobs(action="list")` to show state before destructive deletes.
- Require clear intent before calling delete actions.
- Use `facefusion_run_jobs(skip_nsfw_check=true)` only when the user explicitly asks to bypass FaceFusion NSFW detection for queued work.

## References

- `../../resources/commands.md`
- `../../resources/common-workflows.md`
- `../../resources/parameter-mapping.md`
- `references/multi-actor-workflow.md`
