---
name: diagnose-facefusion-failure
description: Diagnose failed FaceFusion runs, downloads, and environment issues through the FaceFusion Local MCP plugin. Use when the user reports that FaceFusion cannot start, a task failed, downloads broke, CUDA did not load, or a job exited with errors.
---

# Diagnose Facefusion Failure

Use this skill to reason from an observed failure toward the narrowest likely fix.

## Workflow

1. Start from the failing tool result and summarize the concrete symptom.
2. Read `../../resources/troubleshooting.md`.
3. If the issue looks environmental, call `facefusion_health_check`.
4. If the issue looks asset-related, call `facefusion_download_models`.
5. Only suggest retries after identifying whether the issue is environment, inputs, flags, or queue state.

## Tool Rules

- Prefer diagnosis over immediate reruns.
- Use `facefusion_manage_jobs(action="list")` when debugging job state.
- Use `facefusion_list_capabilities` if the user is selecting an unsupported provider or processor.

## References

- `../../resources/troubleshooting.md`
- `../../resources/execution-providers.md`
- `../../resources/parameter-mapping.md`
