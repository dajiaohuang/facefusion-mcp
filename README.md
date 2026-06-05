# FaceFusion MCP

MCP server and Codex plugin for driving a local [FaceFusion](https://github.com/facefusion/facefusion) installation through tools, resources, and prompts, with a strong focus on conversational multi-actor and multi-face orchestration, preview approval, shot-level retry workflows, and confirmation-gated install/setup when FaceFusion is missing.

## Featured Workflow

FaceFusion MCP is built for more than one-off swaps. Its standout workflow is conversational multi-actor orchestration:

- map multiple source faces to named roles
- split a target video into shot-level tasks
- mix shot-level operations such as face swap, lip sync, enhancement, and background removal
- generate preview tasks before risky final renders
- approve or reject previews to control final promotion
- retry only the affected shot instead of rebuilding the entire queue

This makes it practical for an agent to coordinate multi-role, multi-face projects with a `cast -> shots -> preview -> approval -> retry` loop instead of forcing users to hand-author large FaceFusion command lines.

It can also detect when FaceFusion is not installed or not fully set up yet, then propose an install/setup plan and only execute it after explicit confirmation.

## What It Provides

- `17` executable MCP tools for:
  - health checks
  - install and setup automation
  - capability discovery
  - model downloads
  - one-off runs
  - batch runs
  - benchmarks
  - job creation
  - job step updates
  - job execution
  - job management
  - multi-actor cast definition
  - multi-actor shot planning
  - multi-actor plan building
  - multi-actor job materialization
  - preview approval
  - failed task retry
- `7` reference resources for:
  - commands
  - processors
  - execution providers
  - parameter mapping
  - common workflows
  - troubleshooting
  - multi-actor workflow
- `4` prompts for:
  - direct task execution
  - environment preparation
  - job orchestration
  - failure diagnosis

## Repository Layout

```text
.codex-plugin/plugin.json
.mcp.json
resources/
scripts/server.py
skills/
```

## Included Skills

- `run-facefusion-task`
- `prepare-facefusion-environment`
- `orchestrate-facefusion-jobs`
- `diagnose-facefusion-failure`
- `coordinate-multi-actor-facefusion`

The `coordinate-multi-actor-facefusion` skill is the main entrypoint for the multi-actor workflow above.

## Requirements

- Windows
- Python with the `mcp` package available on `PATH`
- A local FaceFusion checkout
- A FaceFusion Python environment that can run `facefusion.py`
- `ffmpeg` on `PATH`

## FaceFusion Path Resolution

The server resolves FaceFusion in this order:

1. `facefusion_root` tool argument
2. `FACEFUSION_ROOT` environment variable
3. repository-adjacent autodetection

It resolves the Python interpreter in this order:

1. `python_path` tool argument
2. `FACEFUSION_PYTHON` environment variable
3. `<facefusion_root>/.venv/Scripts/python.exe`

## Local Setup

Example PowerShell setup:

```powershell
$env:FACEFUSION_ROOT="D:\facefusion-3.6.1"
$env:FACEFUSION_PYTHON="D:\facefusion-3.6.1\.venv\Scripts\python.exe"
python .\scripts\server.py --stdio
```

## MCP Tools

- `facefusion_health_check`
- `facefusion_install_or_setup`
- `facefusion_list_capabilities`
- `facefusion_download_models`
- `facefusion_run_job`
- `facefusion_batch_run`
- `facefusion_benchmark`
- `facefusion_create_job`
- `facefusion_update_job_steps`
- `facefusion_run_jobs`
- `facefusion_manage_jobs`
- `facefusion_define_cast`
- `facefusion_plan_shots`
- `facefusion_build_multi_actor_plan`
- `facefusion_materialize_multi_actor_jobs`
- `facefusion_approve_preview`
- `facefusion_retry_failed_task`

## Resources

- `facefusion://reference/commands`
- `facefusion://reference/processors`
- `facefusion://reference/execution-providers`
- `facefusion://reference/parameter-mapping`
- `facefusion://recipes/common-workflows`
- `facefusion://reference/troubleshooting`
- `facefusion://recipes/multi-actor-workflow`

## Prompts

- `run-facefusion-task`
- `prepare-facefusion-environment`
- `orchestrate-facefusion-jobs`
- `diagnose-facefusion-failure`

## Validation

Plugin validation:

```powershell
python C:\Users\dajiaohuang\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

Example direct server smoke test:

```powershell
python -c "import importlib.util, pathlib; p=pathlib.Path(r'.\scripts\server.py'); spec=importlib.util.spec_from_file_location('ffmcp', p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print([t.name for t in m.mcp._tool_manager.list_tools()])"
```
