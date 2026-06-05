# FaceFusion Local MCP

Local MCP server and Codex plugin for driving a local [FaceFusion](https://github.com/facefusion/facefusion) installation through tools, resources, and prompts.

## What It Provides

- `10` executable MCP tools for:
  - health checks
  - capability discovery
  - model downloads
  - one-off runs
  - batch runs
  - benchmarks
  - job creation
  - job step updates
  - job execution
  - job management
- `6` reference resources for:
  - commands
  - processors
  - execution providers
  - parameter mapping
  - common workflows
  - troubleshooting
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
- `facefusion_list_capabilities`
- `facefusion_download_models`
- `facefusion_run_job`
- `facefusion_batch_run`
- `facefusion_benchmark`
- `facefusion_create_job`
- `facefusion_update_job_steps`
- `facefusion_run_jobs`
- `facefusion_manage_jobs`

## Resources

- `facefusion://reference/commands`
- `facefusion://reference/processors`
- `facefusion://reference/execution-providers`
- `facefusion://reference/parameter-mapping`
- `facefusion://recipes/common-workflows`
- `facefusion://reference/troubleshooting`

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
