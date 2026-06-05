---
name: prepare-facefusion-environment
description: Prepare and validate the local FaceFusion environment through the FaceFusion Local MCP plugin. Use when the user asks to check whether FaceFusion can run, inspect available providers or processors, preload models, or benchmark CUDA, TensorRT, or CPU execution before running media tasks.
---

# Prepare Facefusion Environment

Use this skill when the user wants readiness, downloads, capability inspection, or performance guidance rather than an immediate media-processing run.

## Workflow

1. Start with `facefusion_health_check`.
2. If the user asks what is available, call `facefusion_list_capabilities`.
3. If the install is missing or repairing models, call `facefusion_download_models`.
4. If the user asks about speed, providers, or tuning, read `../../resources/execution-providers.md` and call `facefusion_benchmark`.

## Tool Rules

- Do not launch `facefusion_run_job` or `facefusion_batch_run` from this skill unless the user explicitly pivots into execution.
- Use `facefusion_benchmark` only when the user cares about provider choice, throughput, or tradeoffs.
- Use `../../resources/troubleshooting.md` when the environment is unhealthy.

## References

- `../../resources/execution-providers.md`
- `../../resources/troubleshooting.md`
- `../../resources/commands.md`
