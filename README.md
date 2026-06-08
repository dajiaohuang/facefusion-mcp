# FaceFusion MCP

MCP server and Codex plugin for driving a local [FaceFusion](https://github.com/facefusion/facefusion) installation through tools, resources, and prompts, with a strong focus on both headless execution and interactive UI launch, broader FaceFusion capability exposure, reusable presets, conversational multi-actor and multi-face orchestration, plan visualization, preview approval, shot-level retry workflows, and confirmation-gated install/setup when FaceFusion is missing.

## Featured Workflow

FaceFusion MCP is built for more than one-off swaps. Its standout workflow is conversational multi-actor orchestration:

- map multiple source faces to named roles
- split a target video into shot-level tasks
- mix shot-level operations such as face swap, lip sync, enhancement, and background removal
- generate preview tasks before risky final renders
- approve or reject previews to control final promotion
- retry only the affected shot instead of rebuilding the entire queue

This makes it practical for an agent to coordinate multi-role, multi-face projects with a `cast -> shots -> preview -> approval -> retry` loop instead of forcing users to hand-author large FaceFusion command lines.

After `plan.json` is generated, the plugin can also render a standalone HTML plan viewer so the queue is easy to inspect in a browser before previews are approved or finals are promoted.

It can also detect when FaceFusion is not installed or not fully set up yet, then propose an install/setup plan and only execute it after explicit confirmation.

## What It Provides

- `31` executable MCP tools for:
  - health checks
  - install and setup automation
  - optional NSFW-check bypass at plugin runtime
  - expanded capability discovery
  - preset discovery
  - queue and worker status checks
  - task-oriented face swap, lip sync, enhancement, colorization, cutout, editing, aging, and debugging shortcuts
  - model downloads
  - one-off headless runs
  - interactive UI launch
  - batch runs
  - benchmarks
  - job creation
  - job step updates
  - job execution
  - job management
  - multi-actor cast definition
  - multi-actor shot planning
  - multi-actor plan building
  - multi-actor plan visualization
  - multi-actor job materialization
  - preview approval
  - failed task retry
- `8` reference resources for:
  - commands
  - processors
  - execution providers
  - parameter mapping
  - common workflows
  - troubleshooting
  - multi-actor workflow
  - presets
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
3. `facefusion.env.json` stored in the plugin root
4. repository-adjacent autodetection

It resolves the Python interpreter in this order:

1. `python_path` tool argument
2. `FACEFUSION_PYTHON` environment variable
3. `facefusion.env.json` stored in the plugin root
4. `<facefusion_root>/.venv/Scripts/python.exe`

## Local Setup

Example PowerShell setup:

```powershell
$env:FACEFUSION_ROOT="D:\facefusion-3.6.1"
$env:FACEFUSION_PYTHON="D:\facefusion-3.6.1\.venv\Scripts\python.exe"
python .\scripts\server.py --stdio
```

## If FaceFusion Is Missing

After this plugin is installed, you can ask the agent to install or set up FaceFusion for you.

The expected flow is:

1. The agent runs `facefusion_health_check`.
2. If FaceFusion is missing or incomplete, the tool reports:
   - `needs_install` or `needs_setup`
   - `missing_components`
   - `suggested_install_root`
   - `can_auto_install_or_setup`
3. The agent explains the proposed install/setup plan and asks for confirmation.
4. Only after explicit confirmation does the agent call `facefusion_install_or_setup(confirmed=true, ...)`.
5. The install tool then:
   - clones or reuses a FaceFusion checkout
   - creates or reuses a `.venv`
   - upgrades `pip`
   - runs `install.py --skip-conda --onnxruntime <variant>`
   - optionally preloads models
6. The agent runs `facefusion_health_check` again and reports the new status.

Notes:

- Installation is confirmation-gated. The plugin does not install FaceFusion automatically without user approval.
- `ffmpeg` is checked by the health check, but this plugin currently does not install `ffmpeg` for the user.
- The default install path is either the user-provided `install_root`, `FACEFUSION_ROOT`, an existing detected checkout, or a plugin-managed fallback directory.
- After a successful plugin-managed install or setup, the resolved `facefusion_root` and `python_path` are persisted to `facefusion.env.json` in the plugin root.

Install path priority:

1. `install_root` passed to `facefusion_install_or_setup`
2. `FACEFUSION_ROOT`
3. an already detected FaceFusion checkout
4. `plugins/facefusion-local/.facefusion-runtime`

The Python environment is created inside the chosen install root at:

- `.venv\Scripts\python.exe`
- `.venv\Scripts\pip.exe`

## MCP Tools

- `facefusion_health_check`
- `facefusion_install_or_setup`
- `facefusion_list_capabilities`
- `facefusion_list_presets`
- `facefusion_check_queue`
- `facefusion_download_models`
- `facefusion_task_face_swap`
- `facefusion_task_lip_sync`
- `facefusion_task_remove_background`
- `facefusion_task_enhance_face`
- `facefusion_task_enhance_frame`
- `facefusion_task_colorize_frames`
- `facefusion_task_edit_face`
- `facefusion_task_restore_expression`
- `facefusion_task_modify_age`
- `facefusion_task_debug_faces`
- `facefusion_run_job`
- `facefusion_launch_ui`
- `facefusion_batch_run`
- `facefusion_benchmark`
- `facefusion_create_job`
- `facefusion_update_job_steps`
- `facefusion_run_jobs`
- `facefusion_manage_jobs`
- `facefusion_define_cast`
- `facefusion_plan_shots`
- `facefusion_build_multi_actor_plan`
- `facefusion_render_plan_ui`
- `facefusion_materialize_multi_actor_jobs`
- `facefusion_approve_preview`
- `facefusion_retry_failed_task`

## Plugin Runtime Options

The plugin supports a plugin-level `skip_nsfw_check` switch.

Use it when you want the plugin to launch FaceFusion through a wrapper that disables `facefusion.content_analyser` for that run without modifying the FaceFusion source tree.

How to use it:

- `facefusion_run_job`: pass `misc_options.skip_nsfw_check=true`
- `facefusion_launch_ui`: pass `misc_options.skip_nsfw_check=true`
- `facefusion_batch_run`: pass `misc_options.skip_nsfw_check=true`
- `facefusion_run_jobs`: pass `skip_nsfw_check=true`

Scope:

- this is a plugin-only runtime behavior
- it is not forwarded as a FaceFusion CLI flag
- it applies only to runs launched through this plugin

## Environment Defaults

The plugin can also read environment-level runtime defaults from `facefusion.env.json`.

Useful sections:

- `default_ui_mode`
- `tool_defaults.common`
- `tool_defaults.run_job`
- `tool_defaults.launch_ui`
- `tool_defaults.batch_run`
- `tool_defaults.benchmark`
- `task_defaults.common`
- `task_defaults.face_swap`
- `task_defaults.lip_sync`
- `task_defaults.background_remove`
- `task_defaults.face_enhance`
- `task_defaults.frame_enhance`
- `task_defaults.frame_colorize`
- `task_defaults.face_edit`
- `task_defaults.expression_restore`
- `task_defaults.age_modify`
- `task_defaults.face_debug`

Precedence:

1. built-in MCP preset defaults
2. `facefusion.env.json`
3. explicit tool arguments for the current call

This means you can keep your preferred default quality or speed policy in `facefusion.env.json`, while still overriding it per task when needed.

`default_ui_mode` controls whether the agent should prefer the visual review flow by default:

- `true`: after the initial prompt, generate the initial draft state such as cast, reference groups, shot-operation draft, and plan draft, then render the HTML review UI and continue asking follow-up questions until all details are filled
- `false`: after the initial prompt, still generate the initial draft state first, but continue by dialogue only, summarizing the current cast, references, shot operations, and plan state until all missing details are filled without depending on the HTML review pages

## Head And Headless

- Prefer the `facefusion_task_*` tools for normal work.
- Use `facefusion_run_job` for a direct non-UI execution path that maps to `headless-run`.
- Use `facefusion_launch_ui` when you want FaceFusion's interactive `run` mode, optionally with `--open-browser`, `--ui-layouts`, `--ui-workflow`, and prefilled source/target paths.
- Use `dry_run=true` on `facefusion_launch_ui` when you want to inspect the exact launch command before opening the UI.

## Task Shortcuts

The MCP surface now prefers task-oriented shortcut tools over raw parameter assembly.

Primary task tools:

- `facefusion_task_face_swap`
- `facefusion_task_lip_sync`
- `facefusion_task_remove_background`
- `facefusion_task_enhance_face`
- `facefusion_task_enhance_frame`
- `facefusion_task_colorize_frames`
- `facefusion_task_edit_face`
- `facefusion_task_restore_expression`
- `facefusion_task_modify_age`
- `facefusion_task_debug_faces`

These tools still route through the same validated execution core, but give the agent cleaner task entrypoints.

## Full Capability Surface

`facefusion_list_capabilities` now exposes more than commands and processor names.

It can enumerate:

- commands
- processors
- execution providers
- encoders
- UI layouts and workflows
- download providers and scopes
- memory strategies and runtime ranges
- benchmark modes and resolutions
- face detection, selection, masking, and voice-extractor choices
- processor-specific model choices
- MCP presets

Use `category="all"` for the full catalog.

## Presets

Use `facefusion_list_presets` to inspect the built-in preset library.

The following tools accept `preset`:

- `facefusion_run_job`
- `facefusion_launch_ui`
- `facefusion_batch_run`
- `facefusion_benchmark`

Explicit request fields override preset defaults.

## Plan Viewer

For multi-actor projects, once `facefusion_build_multi_actor_plan` writes `plan.json`, you can call `facefusion_render_plan_ui`.

It reads:

- `cast.json`
- `shots.json`
- `plan.json`

and writes a standalone HTML file by default to:

- `<project_dir>/manifests/plan-view.html`

The generated page shows:

- cast and source-asset overview
- shot list and operations
- task cards for previews and finals
- status, processors, risk, provider, and output-path summaries
- quick filtering by task type and status

## Resources

- `facefusion://reference/commands`
- `facefusion://reference/processors`
- `facefusion://reference/execution-providers`
- `facefusion://reference/parameter-mapping`
- `facefusion://recipes/common-workflows`
- `facefusion://reference/troubleshooting`
- `facefusion://recipes/multi-actor-workflow`
- `facefusion://reference/presets`

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
