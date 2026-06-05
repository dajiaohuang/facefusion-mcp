from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = PLUGIN_ROOT / "resources"
DEFAULT_COMMANDS = [
    "run",
    "headless-run",
    "batch-run",
    "force-download",
    "benchmark",
    "job-list",
    "job-create",
    "job-submit",
    "job-submit-all",
    "job-delete",
    "job-delete-all",
    "job-add-step",
    "job-remix-step",
    "job-insert-step",
    "job-remove-step",
    "job-run",
    "job-run-all",
    "job-retry",
    "job-retry-all",
]
JOB_STATUSES = ["drafted", "queued", "completed", "failed"]
RESOURCE_URIS = {
    "facefusion://reference/commands": RESOURCE_DIR / "commands.md",
    "facefusion://reference/processors": RESOURCE_DIR / "processors.md",
    "facefusion://reference/execution-providers": RESOURCE_DIR / "execution-providers.md",
    "facefusion://reference/parameter-mapping": RESOURCE_DIR / "parameter-mapping.md",
    "facefusion://recipes/common-workflows": RESOURCE_DIR / "common-workflows.md",
    "facefusion://reference/troubleshooting": RESOURCE_DIR / "troubleshooting.md",
}

mcp = FastMCP(
    name="FaceFusion MCP",
    instructions=(
        "Use this server to run the local FaceFusion installation, inspect its capabilities, "
        "read stable references, and render workflow prompts for local media processing."
    ),
)


def _truncate(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def _detect_default_facefusion_root() -> Path:
    env_root = os.environ.get("FACEFUSION_ROOT")
    if env_root:
        return Path(env_root)

    candidates = [
        PLUGIN_ROOT.parent.parent,
        PLUGIN_ROOT.parent,
        PLUGIN_ROOT,
    ]
    for candidate in candidates:
        if (candidate / "facefusion.py").exists():
            return candidate
    return candidates[0]


FACEFUSION_ROOT = _detect_default_facefusion_root()
DEFAULT_PYTHON = Path(os.environ.get("FACEFUSION_PYTHON", FACEFUSION_ROOT / ".venv" / "Scripts" / "python.exe"))


def _facefusion_python(facefusion_root: str | None = None, python_path: str | None = None) -> Path:
    if python_path:
        return Path(python_path)
    if facefusion_root:
        return Path(facefusion_root) / ".venv" / "Scripts" / "python.exe"
    return DEFAULT_PYTHON


def _facefusion_root(facefusion_root: str | None = None) -> Path:
    return Path(facefusion_root) if facefusion_root else FACEFUSION_ROOT


def _run_subprocess(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_summary": _truncate(completed.stdout),
        "stderr_summary": _truncate(completed.stderr),
        "success": completed.returncode == 0,
    }


def _run_facefusion_command(
    command_args: list[str],
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    command = [str(python_exe), "facefusion.py", *command_args]
    return _run_subprocess(command, root)


def _run_facefusion_code(
    code: str,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    injected = (
        f"import sys; sys.path.insert(0, r'{str(root)}'); "
        f"{code}"
    )
    command = [str(python_exe), "-c", injected]
    return _run_subprocess(command, root)


def _bool_to_flag(args: list[str], flag: str, value: Any) -> None:
    if isinstance(value, bool):
        if value:
            args.append(flag)
        return
    if value is None:
        return
    if isinstance(value, list):
        if value:
            args.append(flag)
            args.extend(str(item) for item in value)
        return
    args.extend([flag, str(value)])


def _snake_to_flag(key: str) -> str:
    return "--" + key.replace("_", "-")


def _append_flat_options(args: list[str], values: dict[str, Any] | None, rename: dict[str, str] | None = None) -> None:
    if not values:
        return
    rename = rename or {}
    for key, value in values.items():
        if value is None:
            continue
        flag = _snake_to_flag(rename.get(key, key))
        _bool_to_flag(args, flag, value)


def _parse_json_stdout(result: dict[str, Any], fallback: Any) -> Any:
    if not result["success"]:
        return fallback
    try:
        return json.loads(result["stdout"].strip() or "null")
    except json.JSONDecodeError:
        return fallback


def _models_summary(facefusion_root: str | None = None) -> dict[str, Any]:
    models_dir = _facefusion_root(facefusion_root) / ".assets" / "models"
    if not models_dir.exists():
        return {
            "path": str(models_dir),
            "exists": False,
            "total_files": 0,
            "by_extension": {},
        }
    by_extension: dict[str, int] = {}
    total = 0
    for file_path in models_dir.iterdir():
        if not file_path.is_file():
            continue
        total += 1
        suffix = file_path.suffix.lower() or "<none>"
        by_extension[suffix] = by_extension.get(suffix, 0) + 1
    return {
        "path": str(models_dir),
        "exists": True,
        "total_files": total,
        "by_extension": by_extension,
    }


def _available_processors(facefusion_root: str | None = None) -> list[str]:
    modules_dir = _facefusion_root(facefusion_root) / "facefusion" / "processors" / "modules"
    ignored = {"__init__", "__pycache__", "types", "core"}
    processors = []
    for path in sorted(modules_dir.iterdir()):
        if path.is_dir() and path.name not in ignored and not path.name.startswith("."):
            processors.append(path.name)
        elif path.is_file() and path.suffix == ".py" and path.stem not in ignored:
            processors.append(path.stem)
    return sorted(set(processors))


def _available_providers(facefusion_root: str | None = None, python_path: str | None = None) -> list[str]:
    result = _run_facefusion_code(
        "import json; from facefusion.execution import get_available_execution_providers; "
        "print(json.dumps(get_available_execution_providers()))",
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    return _parse_json_stdout(result, [])


def _available_encoders(facefusion_root: str | None = None, python_path: str | None = None) -> dict[str, Any]:
    result = _run_facefusion_code(
        "import json; from facefusion.ffmpeg import get_available_encoder_set; "
        "print(json.dumps(get_available_encoder_set()))",
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    return _parse_json_stdout(result, {})


def _default_provider(facefusion_root: str | None = None, python_path: str | None = None) -> list[str]:
    providers = _available_providers(facefusion_root=facefusion_root, python_path=python_path)
    if "cuda" in providers:
        return ["cuda"]
    if "cpu" in providers:
        return ["cpu"]
    return providers[:1]


def _build_common_run_args(
    processors: list[str] | None,
    execution: dict[str, Any] | None,
    output_options: dict[str, Any] | None,
    memory_options: dict[str, Any] | None,
    face_options: dict[str, Any] | None,
    download_options: dict[str, Any] | None,
    misc_options: dict[str, Any] | None,
    extra_args: list[str] | None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> list[str]:
    args: list[str] = []
    if processors:
        args.extend(["--processors", *processors])

    normalized_execution = dict(execution or {})
    if "providers" not in normalized_execution or not normalized_execution["providers"]:
        normalized_execution["providers"] = _default_provider(facefusion_root=facefusion_root, python_path=python_path)
    execution_rename = {
        "providers": "execution_providers",
        "device_ids": "execution_device_ids",
        "thread_count": "execution_thread_count",
    }
    output_rename = {
        "image_quality": "output_image_quality",
        "image_scale": "output_image_scale",
        "audio_encoder": "output_audio_encoder",
        "audio_quality": "output_audio_quality",
        "audio_volume": "output_audio_volume",
        "video_encoder": "output_video_encoder",
        "video_preset": "output_video_preset",
        "video_quality": "output_video_quality",
        "video_scale": "output_video_scale",
        "video_fps": "output_video_fps",
    }
    memory_rename = {
        "video_memory_strategy": "video_memory_strategy",
        "system_memory_limit": "system_memory_limit",
    }
    download_rename = {
        "download_providers": "download_providers",
    }
    misc_rename = {
        "log_level": "log_level",
        "halt_on_error": "halt_on_error",
        "keep_temp": "keep_temp",
    }

    sanitized_output = dict(output_options or {})
    sanitized_output.pop("overwrite", None)

    _append_flat_options(args, normalized_execution, execution_rename)
    _append_flat_options(args, sanitized_output, output_rename)
    _append_flat_options(args, memory_options, memory_rename)
    _append_flat_options(args, face_options)
    _append_flat_options(args, download_options, download_rename)
    _append_flat_options(args, misc_options, misc_rename)

    if extra_args:
        args.extend(str(item) for item in extra_args)
    return args


def _require_existing_file(path: str, field_name: str) -> None:
    if not Path(path).is_file():
        raise ValueError(f"{field_name} does not exist or is not a file: {path}")


def _ensure_output_allowed(output_path: str, output_options: dict[str, Any] | None) -> None:
    overwrite = bool((output_options or {}).get("overwrite"))
    if Path(output_path).exists() and not overwrite:
        raise ValueError(f"output_path already exists and overwrite is false: {output_path}")


@mcp.tool(description="Check whether the local FaceFusion installation can run on this machine.", structured_output=True)
def facefusion_health_check(
    facefusion_root: str | None = None,
    python_path: str | None = None,
    include_models: bool = True,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    ffmpeg_check = _run_subprocess(["ffmpeg", "-version"], cwd=root)
    version_check = _run_facefusion_command(["-v"], facefusion_root=facefusion_root, python_path=python_path)
    providers = _available_providers(facefusion_root=facefusion_root, python_path=python_path)
    models = _models_summary(facefusion_root=facefusion_root) if include_models else None
    ready = all(
        [
            root.exists(),
            python_exe.exists(),
            (root / "facefusion.py").exists(),
            ffmpeg_check["success"],
            version_check["success"],
        ]
    )
    return {
        "facefusion_root": str(root),
        "python_path": str(python_exe),
        "facefusion_version": version_check["stdout"].strip(),
        "ffmpeg_available": ffmpeg_check["success"],
        "ffmpeg_summary": ffmpeg_check["stdout_summary"],
        "execution_providers": providers,
        "paths": {
            "facefusion_root_exists": root.exists(),
            "python_exists": python_exe.exists(),
            "entrypoint_exists": (root / "facefusion.py").exists(),
            "models_dir_exists": (root / ".assets" / "models").exists(),
        },
        "models": models,
        "can_run": ready,
        "checks": {
            "version_command": version_check,
            "ffmpeg_command": ffmpeg_check,
        },
    }


@mcp.tool(description="List the current machine's FaceFusion commands, processors, providers, and encoders.", structured_output=True)
def facefusion_list_capabilities(
    category: str = "all",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    capabilities = {
        "commands": DEFAULT_COMMANDS,
        "processors": _available_processors(facefusion_root=facefusion_root),
        "providers": _available_providers(facefusion_root=facefusion_root, python_path=python_path),
        "encoders": _available_encoders(facefusion_root=facefusion_root, python_path=python_path),
    }
    if category == "all":
        return capabilities
    if category not in capabilities:
        raise ValueError(f"Unknown category: {category}")
    return {category: capabilities[category]}


@mcp.tool(description="Download or repair local FaceFusion model assets.", structured_output=True)
def facefusion_download_models(
    scope: str = "lite",
    download_providers: list[str] | None = None,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    args = ["force-download", "--download-scope", scope, "--log-level", log_level]
    if download_providers:
        args.extend(["--download-providers", *download_providers])
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "scope": scope,
        "download_providers": download_providers or [],
        "models": _models_summary(facefusion_root=facefusion_root),
    }


@mcp.tool(description="Run a single local FaceFusion processing task without the UI.", structured_output=True)
def facefusion_run_job(
    source_paths: list[str],
    target_path: str,
    output_path: str,
    processors: list[str] | None = None,
    execution: dict[str, Any] | None = None,
    output_options: dict[str, Any] | None = None,
    memory_options: dict[str, Any] | None = None,
    face_options: dict[str, Any] | None = None,
    download_options: dict[str, Any] | None = None,
    misc_options: dict[str, Any] | None = None,
    extra_args: list[str] | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    for source_path in source_paths:
        _require_existing_file(source_path, "source_paths item")
    _require_existing_file(target_path, "target_path")
    _ensure_output_allowed(output_path, output_options)

    args = ["headless-run", "-s", *source_paths, "-t", target_path, "-o", output_path]
    args.extend(
        _build_common_run_args(
            processors=processors,
            execution=execution,
            output_options=output_options,
            memory_options=memory_options,
            face_options=face_options,
            download_options=download_options,
            misc_options=misc_options,
            extra_args=extra_args,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
    )
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    normalized = {
        "source_paths": source_paths,
        "target_path": target_path,
        "output_path": output_path,
        "processors": processors or [],
        "execution": execution or {"providers": _default_provider(facefusion_root=facefusion_root, python_path=python_path)},
        "output_options": output_options or {},
        "memory_options": memory_options or {},
        "face_options": face_options or {},
        "download_options": download_options or {},
        "misc_options": misc_options or {"log_level": "info"},
        "extra_args": extra_args or [],
    }
    return {
        **result,
        "normalized_request": normalized,
        "output_path": output_path,
        "output_exists": Path(output_path).exists(),
    }


@mcp.tool(description="Run a batch FaceFusion workflow from file patterns.", structured_output=True)
def facefusion_batch_run(
    source_pattern: str,
    target_pattern: str,
    output_pattern: str,
    processors: list[str] | None = None,
    execution: dict[str, Any] | None = None,
    output_options: dict[str, Any] | None = None,
    memory_options: dict[str, Any] | None = None,
    face_options: dict[str, Any] | None = None,
    download_options: dict[str, Any] | None = None,
    misc_options: dict[str, Any] | None = None,
    extra_args: list[str] | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    args = ["batch-run", "-s", source_pattern, "-t", target_pattern, "-o", output_pattern]
    args.extend(
        _build_common_run_args(
            processors=processors,
            execution=execution,
            output_options=output_options,
            memory_options=memory_options,
            face_options=face_options,
            download_options=download_options,
            misc_options=misc_options,
            extra_args=extra_args,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
    )
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "patterns": {
            "source_pattern": source_pattern,
            "target_pattern": target_pattern,
            "output_pattern": output_pattern,
        },
    }


@mcp.tool(description="Benchmark local FaceFusion providers and processor settings.", structured_output=True)
def facefusion_benchmark(
    processors: list[str] | None = None,
    execution: dict[str, Any] | None = None,
    memory_options: dict[str, Any] | None = None,
    face_options: dict[str, Any] | None = None,
    misc_options: dict[str, Any] | None = None,
    benchmark_options: dict[str, Any] | None = None,
    extra_args: list[str] | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    args = ["benchmark"]
    benchmark_rename = {
        "mode": "benchmark_mode",
        "resolutions": "benchmark_resolutions",
        "cycle_count": "benchmark_cycle_count",
        "temp_path": "temp_path",
    }
    args.extend(
        _build_common_run_args(
            processors=processors,
            execution=execution,
            output_options=None,
            memory_options=memory_options,
            face_options=face_options,
            download_options=None,
            misc_options=misc_options,
            extra_args=None,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
    )
    _append_flat_options(args, benchmark_options, benchmark_rename)
    if extra_args:
        args.extend(str(item) for item in extra_args)
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "benchmark_options": benchmark_options or {},
    }


@mcp.tool(description="Create a drafted FaceFusion job.", structured_output=True)
def facefusion_create_job(
    job_id: str,
    jobs_path: str | None = None,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    args = ["job-create", job_id, "--log-level", log_level]
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "job_id": job_id,
        "jobs_path": jobs_path or ".jobs",
    }


@mcp.tool(description="Add, insert, remix, or remove steps within a drafted FaceFusion job.", structured_output=True)
def facefusion_update_job_steps(
    action: str,
    job_id: str,
    step_index: int | None = None,
    step_request: dict[str, Any] | None = None,
    jobs_path: str | None = None,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    action_map = {
        "add": "job-add-step",
        "insert": "job-insert-step",
        "remix": "job-remix-step",
        "remove": "job-remove-step",
    }
    if action not in action_map:
        raise ValueError(f"Unknown action: {action}")
    if action in {"insert", "remix", "remove"} and step_index is None:
        raise ValueError(f"step_index is required for action '{action}'")

    args = [action_map[action], job_id]
    if step_index is not None:
        args.append(str(step_index))
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])

    if action != "remove":
        if step_request is None:
            raise ValueError("step_request is required for add, insert, or remix")
        source_paths = step_request.get("source_paths")
        target_path = step_request.get("target_path")
        output_path = step_request.get("output_path")
        if action != "remix":
            if not source_paths or not target_path or not output_path:
                raise ValueError("step_request must include source_paths, target_path, and output_path")
            args.extend(["-s", *source_paths, "-t", target_path, "-o", output_path])
        else:
            if source_paths:
                args.extend(["-s", *source_paths])
            if output_path:
                args.extend(["-o", output_path])
        args.extend(
            _build_common_run_args(
                processors=step_request.get("processors"),
                execution=None,
                output_options=step_request.get("output_options"),
                memory_options=None,
                face_options=step_request.get("face_options"),
                download_options=None,
                misc_options={"log_level": log_level},
                extra_args=step_request.get("extra_args"),
                facefusion_root=facefusion_root,
                python_path=python_path,
            )
        )
    else:
        args.extend(["--log-level", log_level])

    if "--log-level" not in args:
        args.extend(["--log-level", log_level])
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "action": action,
        "job_id": job_id,
        "step_index": step_index,
    }


@mcp.tool(description="Submit, run, or retry queued FaceFusion jobs.", structured_output=True)
def facefusion_run_jobs(
    mode: str,
    job_id: str | None = None,
    jobs_path: str | None = None,
    halt_on_error: bool = False,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    mode_map = {
        "submit": "job-submit",
        "submit_all": "job-submit-all",
        "run": "job-run",
        "run_all": "job-run-all",
        "retry": "job-retry",
        "retry_all": "job-retry-all",
    }
    if mode not in mode_map:
        raise ValueError(f"Unknown mode: {mode}")
    single_modes = {"submit", "run", "retry"}
    if mode in single_modes and not job_id:
        raise ValueError(f"job_id is required for mode '{mode}'")
    args = [mode_map[mode]]
    if job_id:
        args.append(job_id)
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])
    if halt_on_error:
        args.append("--halt-on-error")
    args.extend(["--log-level", log_level])
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "mode": mode,
        "job_id": job_id,
    }


@mcp.tool(description="List or delete FaceFusion jobs.", structured_output=True)
def facefusion_manage_jobs(
    action: str,
    job_status: str | None = None,
    job_id: str | None = None,
    jobs_path: str | None = None,
    halt_on_error: bool = False,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    if action == "list":
        statuses = [job_status] if job_status else JOB_STATUSES
        outputs = []
        overall_success = True
        for status in statuses:
            args = ["job-list", status, "--log-level", log_level]
            if jobs_path:
                args.extend(["--jobs-path", jobs_path])
            result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
            outputs.append({"job_status": status, **result})
            overall_success = overall_success and result["success"]
        return {
            "action": action,
            "results": outputs,
            "success": overall_success,
        }

    if action == "delete":
        if not job_id:
            raise ValueError("job_id is required for delete")
        args = ["job-delete", job_id, "--log-level", log_level]
        if jobs_path:
            args.extend(["--jobs-path", jobs_path])
        result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
        return {"action": action, "job_id": job_id, **result}

    if action == "delete_all":
        args = ["job-delete-all", "--log-level", log_level]
        if jobs_path:
            args.extend(["--jobs-path", jobs_path])
        if halt_on_error:
            args.append("--halt-on-error")
        result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
        return {"action": action, **result}

    raise ValueError(f"Unknown action: {action}")


@mcp.resource("facefusion://reference/commands", name="facefusion-commands", description="Static reference for FaceFusion command families.")
def resource_commands() -> str:
    return (RESOURCE_DIR / "commands.md").read_text(encoding="utf-8")


@mcp.resource("facefusion://reference/processors", name="facefusion-processors", description="Static reference for FaceFusion processors.")
def resource_processors() -> str:
    return (RESOURCE_DIR / "processors.md").read_text(encoding="utf-8")


@mcp.resource("facefusion://reference/execution-providers", name="facefusion-execution-providers", description="Static reference for FaceFusion execution providers.")
def resource_execution_providers() -> str:
    return (RESOURCE_DIR / "execution-providers.md").read_text(encoding="utf-8")


@mcp.resource("facefusion://reference/parameter-mapping", name="facefusion-parameter-mapping", description="Static reference for MCP request to FaceFusion CLI flag mapping.")
def resource_parameter_mapping() -> str:
    return (RESOURCE_DIR / "parameter-mapping.md").read_text(encoding="utf-8")


@mcp.resource("facefusion://recipes/common-workflows", name="facefusion-common-workflows", description="Static workflow recipes for common FaceFusion tasks.")
def resource_common_workflows() -> str:
    return (RESOURCE_DIR / "common-workflows.md").read_text(encoding="utf-8")


@mcp.resource("facefusion://reference/troubleshooting", name="facefusion-troubleshooting", description="Static troubleshooting notes for common FaceFusion failures.")
def resource_troubleshooting() -> str:
    return (RESOURCE_DIR / "troubleshooting.md").read_text(encoding="utf-8")


@mcp.prompt(name="run-facefusion-task", description="Route a normal media-processing request into the right FaceFusion tool sequence.")
def prompt_run_facefusion_task() -> str:
    return (
        "Use FaceFusion Local to fulfill a direct media-processing request. "
        "First decide whether the user wants a single task or a pattern-based batch. "
        "If environment readiness is unknown, call facefusion_health_check. "
        "If the task is missing models or looks like a first run, call facefusion_download_models. "
        "Use facefusion://reference/processors and facefusion://recipes/common-workflows to choose processors. "
        "Then call facefusion_run_job for one task or facefusion_batch_run for a batch. "
        "Do not use job-management tools unless the user explicitly wants a queue or drafts."
    )


@mcp.prompt(name="prepare-facefusion-environment", description="Prepare the local FaceFusion environment before larger tasks.")
def prompt_prepare_facefusion_environment() -> str:
    return (
        "Prepare the local FaceFusion environment. "
        "Start with facefusion_health_check. "
        "If the user asks what is available, call facefusion_list_capabilities. "
        "If models are missing or the user wants a preload, call facefusion_download_models. "
        "If the user asks about performance or provider choice, call facefusion_benchmark. "
        "Do not launch processing jobs in this workflow unless the user explicitly pivots into a run request."
    )


@mcp.prompt(name="orchestrate-facefusion-jobs", description="Build and operate drafted, queued, or retried FaceFusion jobs.")
def prompt_orchestrate_facefusion_jobs() -> str:
    return (
        "Use FaceFusion job tools for queue-oriented workflows. "
        "Create a draft with facefusion_create_job, then use facefusion_update_job_steps to add, insert, remix, or remove steps. "
        "Inspect the queue with facefusion_manage_jobs. "
        "Submit, run, or retry jobs with facefusion_run_jobs. "
        "Prefer this path only when the user wants drafts, queues, retries, or step-by-step orchestration."
    )


@mcp.prompt(name="diagnose-facefusion-failure", description="Diagnose a failed FaceFusion task or environment issue.")
def prompt_diagnose_facefusion_failure() -> str:
    return (
        "Diagnose a FaceFusion failure. "
        "Start from the failing tool result and summarize the concrete error. "
        "Read facefusion://reference/troubleshooting for likely causes and recovery paths. "
        "If the failure looks environmental, rerun facefusion_health_check. "
        "If the failure looks like missing assets, call facefusion_download_models. "
        "Avoid blind retries before identifying whether the issue is configuration, environment, or inputs."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", help="Run the MCP server over stdio.")
    args = parser.parse_args()
    if args.stdio:
        mcp.run("stdio")
        return
    parser.error("Use --stdio to run this MCP server.")


if __name__ == "__main__":
    main()
