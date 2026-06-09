from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = PLUGIN_ROOT / "resources"
ENV_CONFIG_PATH = PLUGIN_ROOT / "facefusion.env.json"
RUNNER_STATE_PATH = PLUGIN_ROOT / "facefusion.runner.json"
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
FACEFUSION_REPO_URL = "https://github.com/facefusion/facefusion.git"
JOB_STATUSES = ["drafted", "queued", "completed", "failed"]
MULTI_ACTOR_OPERATION_PROFILES: dict[str, dict[str, Any]] = {
    "face_swap": {
        "default_processors": ["face_swapper"],
        "source_asset_kind": "face",
        "roles_required": True,
        "supports_multi_role": True,
        "preview_default": "shot",
        "quality_enhancer": "face_enhancer",
    },
    "lip_sync": {
        "default_processors": ["lip_syncer"],
        "source_asset_kind": "audio",
        "roles_required": True,
        "supports_multi_role": False,
        "preview_default": True,
        "quality_enhancer": "face_enhancer",
    },
    "face_enhance": {
        "default_processors": ["face_enhancer"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "background_remove": {
        "default_processors": ["background_remover"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "frame_enhance": {
        "default_processors": ["frame_enhancer"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "frame_colorize": {
        "default_processors": ["frame_colorizer"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "expression_restore": {
        "default_processors": ["expression_restorer"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "face_edit": {
        "default_processors": ["face_editor"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
    "age_modify": {
        "default_processors": ["age_modifier"],
        "source_asset_kind": None,
        "roles_required": False,
        "supports_multi_role": True,
        "preview_default": False,
    },
}
PRESET_LIBRARY: dict[str, dict[str, Any]] = {
    "fast_preview_swap": {
        "description": "Fast preview-oriented face swap with lighter memory usage and quick video encoding.",
        "processors": ["face_swapper"],
        "execution": {"providers": ["cuda"], "thread_count": 1},
        "output_options": {"video_preset": "veryfast", "video_quality": 60},
        "memory_options": {"video_memory_strategy": "strict"},
        "face_options": {
            "face_detector_model": "retinaface",
            "face_selector_mode": "one",
            "face_mask_types": ["box", "occlusion"],
        },
        "misc_options": {"log_level": "info"},
        "recommended_for": ["quick previews", "approval passes", "single-face video checks"],
    },
    "balanced_face_swap": {
        "description": "Balanced default for general image or video face swapping.",
        "processors": ["face_swapper", "face_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"video_preset": "medium", "video_quality": 80},
        "memory_options": {"video_memory_strategy": "moderate"},
        "face_options": {
            "face_detector_model": "retinaface",
            "face_selector_mode": "one",
            "face_mask_types": ["box", "occlusion", "region"],
        },
        "misc_options": {"log_level": "info"},
        "recommended_for": ["default direct swaps", "most local tasks"],
    },
    "quality_face_swap": {
        "description": "Higher-quality swap preset with more expensive restoration defaults.",
        "processors": ["face_swapper", "face_enhancer", "frame_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"video_preset": "slow", "video_quality": 90},
        "memory_options": {"video_memory_strategy": "tolerant"},
        "face_options": {
            "face_detector_model": "retinaface",
            "face_selector_mode": "reference",
            "face_mask_types": ["box", "occlusion", "region"],
        },
        "misc_options": {"log_level": "info"},
        "recommended_for": ["final renders", "higher-detail shots", "multi-face review-approved work"],
    },
    "multi_face_reference": {
        "description": "Reference-tracking oriented preset for multi-face or same-frame role swaps.",
        "processors": ["face_swapper", "face_enhancer"],
        "execution": {"providers": ["cuda"]},
        "memory_options": {"video_memory_strategy": "moderate"},
        "face_options": {
            "face_selector_mode": "reference",
            "face_selector_order": "left-right",
            "face_mask_types": ["box", "occlusion", "region"],
            "reference_face_distance": 0.6,
        },
        "misc_options": {"log_level": "info"},
        "recommended_for": ["same-frame multi-face swaps", "multi-actor shots"],
    },
    "lip_sync_clean": {
        "description": "Lip-sync focused preset with conservative masking and face cleanup.",
        "processors": ["lip_syncer", "face_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"video_preset": "medium", "video_quality": 82},
        "memory_options": {"video_memory_strategy": "moderate"},
        "face_options": {
            "face_selector_mode": "one",
            "face_mask_types": ["box", "occlusion", "area"],
            "face_mask_areas": ["mouth"],
        },
        "misc_options": {"log_level": "info"},
        "recommended_for": ["talking-head lip sync", "single speaking role shots"],
    },
    "portrait_enhance": {
        "description": "Portrait cleanup preset for face restoration without identity transfer.",
        "processors": ["face_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"image_quality": 95},
        "memory_options": {"video_memory_strategy": "moderate"},
        "face_options": {"face_selector_mode": "many"},
        "misc_options": {"log_level": "info"},
        "recommended_for": ["portrait cleanup", "restoration passes"],
    },
    "frame_restore": {
        "description": "Whole-frame enhancement preset for video upscaling and cleanup.",
        "processors": ["frame_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"video_preset": "medium", "video_quality": 88},
        "memory_options": {"video_memory_strategy": "tolerant"},
        "misc_options": {"log_level": "info"},
        "recommended_for": ["global frame cleanup", "video restoration"],
    },
    "background_cutout": {
        "description": "Background removal preset for subject isolation and cutout tasks.",
        "processors": ["background_remover"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"image_quality": 95},
        "memory_options": {"video_memory_strategy": "moderate"},
        "misc_options": {"log_level": "info"},
        "recommended_for": ["cutouts", "subject isolation", "background removal"],
    },
    "archive_colorize": {
        "description": "Frame colorization preset for grayscale or archival material.",
        "processors": ["frame_colorizer", "frame_enhancer"],
        "execution": {"providers": ["cuda"]},
        "output_options": {"video_preset": "medium", "video_quality": 85},
        "memory_options": {"video_memory_strategy": "tolerant"},
        "misc_options": {"log_level": "info"},
        "recommended_for": ["archive colorization", "grayscale footage"],
    },
    "face_debug_overlay": {
        "description": "Debug visualization preset for bounding boxes, landmarks, and mask inspection.",
        "processors": ["face_debugger"],
        "execution": {"providers": ["cpu"]},
        "face_options": {
            "face_debugger_items": ["bounding-box", "face-landmark-5", "face-mask"],
            "face_mask_types": ["box", "occlusion", "region"],
        },
        "misc_options": {"log_level": "debug"},
        "recommended_for": ["detector debugging", "mask inspection", "pipeline troubleshooting"],
    },
}
RESOURCE_URIS = {
    "facefusion://reference/commands": RESOURCE_DIR / "commands.md",
    "facefusion://reference/processors": RESOURCE_DIR / "processors.md",
    "facefusion://reference/execution-providers": RESOURCE_DIR / "execution-providers.md",
    "facefusion://reference/parameter-mapping": RESOURCE_DIR / "parameter-mapping.md",
    "facefusion://recipes/common-workflows": RESOURCE_DIR / "common-workflows.md",
    "facefusion://reference/troubleshooting": RESOURCE_DIR / "troubleshooting.md",
    "facefusion://recipes/multi-actor-workflow": RESOURCE_DIR / "multi-actor-workflow.md",
    "facefusion://reference/presets": RESOURCE_DIR / "presets.md",
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


def _read_env_config() -> dict[str, Any]:
    if not ENV_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(ENV_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_env_config(payload: dict[str, Any]) -> None:
    ENV_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _default_skip_nsfw_check() -> bool:
    return bool(_read_env_config().get("default_skip_nsfw_check", False))


def _default_enqueue_tasks() -> bool:
    return bool(_read_env_config().get("default_enqueue_tasks", False))


def _default_background_queue_runner() -> bool:
    return bool(_read_env_config().get("default_background_queue_runner", False))


def _default_ui_mode() -> bool:
    env_config = _read_env_config()
    if "default_ui_mode" not in env_config:
        return True
    return bool(env_config.get("default_ui_mode"))


def _merge_deep_dict(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_deep_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _default_multi_actor_defaults() -> dict[str, Any]:
    env_config = _read_env_config()
    payload = env_config.get("multi_actor_defaults")
    if not isinstance(payload, dict):
        return {"default_shot_operations": [], "operation_defaults": {}}
    default_shot_operations = payload.get("default_shot_operations")
    operation_defaults = payload.get("operation_defaults")
    return {
        "default_shot_operations": list(default_shot_operations or []),
        "operation_defaults": dict(operation_defaults or {}),
    }


def _multi_actor_operation_defaults(operation_type: str) -> dict[str, Any]:
    defaults = _default_multi_actor_defaults()
    operation_defaults = defaults.get("operation_defaults") or {}
    payload = operation_defaults.get(operation_type)
    if not isinstance(payload, dict):
        return {}
    return {
        "processors": list(payload.get("processors") or []),
        "processor_options": dict(payload.get("processor_options") or {}),
        "face_options": dict(payload.get("face_options") or {}),
        "output_options": dict(payload.get("output_options") or {}),
        "misc_options": dict(payload.get("misc_options") or {}),
        "extra_args": list(payload.get("extra_args") or []),
    }


def _default_shot_operations() -> list[str]:
    defaults = _default_multi_actor_defaults()
    return [str(item) for item in (defaults.get("default_shot_operations") or []) if item]


def _read_named_defaults(bucket_name: str, name: str) -> dict[str, Any]:
    bucket = _read_env_config().get(bucket_name)
    if not isinstance(bucket, dict):
        return {
            "preset": None,
            "processors": [],
            "execution": {},
            "output_options": {},
            "memory_options": {},
            "face_options": {},
            "download_options": {},
            "misc_options": {},
            "extra_args": [],
        }
    common = bucket.get("common")
    specific = bucket.get(name)
    common = common if isinstance(common, dict) else {}
    specific = specific if isinstance(specific, dict) else {}
    common_processors = common.get("processors") or common.get("default_processors") or []
    specific_processors = specific.get("processors") or specific.get("default_processors") or []
    return {
        "preset": specific.get("preset", common.get("preset")),
        "processors": list(specific_processors or common_processors or []),
        "execution": _merge_option_dict(common.get("execution"), specific.get("execution")),
        "output_options": _merge_option_dict(common.get("output_options"), specific.get("output_options")),
        "memory_options": _merge_option_dict(common.get("memory_options"), specific.get("memory_options")),
        "face_options": _merge_option_dict(common.get("face_options"), specific.get("face_options")),
        "download_options": _merge_option_dict(common.get("download_options"), specific.get("download_options")),
        "misc_options": _merge_option_dict(common.get("misc_options"), specific.get("misc_options")),
        "extra_args": list(specific.get("extra_args") or common.get("extra_args") or []),
    }


def _resolve_runtime_bundle(
    preset: str | None,
    *,
    defaults_bucket: str,
    defaults_name: str,
    fallback_processors: list[str] | None,
    processors: list[str] | None,
    execution: dict[str, Any] | None,
    output_options: dict[str, Any] | None,
    memory_options: dict[str, Any] | None,
    face_options: dict[str, Any] | None,
    download_options: dict[str, Any] | None,
    misc_options: dict[str, Any] | None,
    extra_args: list[str] | None,
) -> tuple[dict[str, Any], str | None]:
    env_defaults = _read_named_defaults(defaults_bucket, defaults_name)
    effective_preset = preset if preset is not None else env_defaults.get("preset")
    if processors is not None:
        effective_processors = list(processors)
    elif env_defaults.get("processors"):
        effective_processors = list(env_defaults["processors"])
    elif fallback_processors is not None:
        effective_processors = list(fallback_processors)
    else:
        effective_processors = None
    resolved = _resolve_preset_bundle(
        effective_preset,
        processors=effective_processors,
        execution=_merge_option_dict(env_defaults.get("execution"), execution),
        output_options=_merge_option_dict(env_defaults.get("output_options"), output_options),
        memory_options=_merge_option_dict(env_defaults.get("memory_options"), memory_options),
        face_options=_merge_option_dict(env_defaults.get("face_options"), face_options),
        download_options=_merge_option_dict(env_defaults.get("download_options"), download_options),
        misc_options=_merge_option_dict(env_defaults.get("misc_options"), misc_options),
        extra_args=_merge_list(env_defaults.get("extra_args"), extra_args),
    )
    return resolved, effective_preset


def _read_runner_state() -> dict[str, Any]:
    if not RUNNER_STATE_PATH.exists():
        return {}
    try:
        return json.loads(RUNNER_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_runner_state(payload: dict[str, Any]) -> None:
    RUNNER_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clear_runner_state() -> None:
    try:
        RUNNER_STATE_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = _run_subprocess(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            cwd=PLUGIN_ROOT,
        )
        text = (result.get("stdout") or "") + (result.get("stderr") or "")
        return str(pid) in text and "No tasks are running" not in text
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _get_active_runner_state() -> dict[str, Any]:
    state = _read_runner_state()
    status = str(state.get("status", ""))
    started_at = float(state.get("started_at", 0) or 0)
    if status == "starting" and started_at and (time.time() - started_at) < 15:
        return state
    pid = int(state.get("pid", 0) or 0)
    if pid and _pid_is_running(pid):
        return state
    if state:
        _clear_runner_state()
    return {}


def _list_jobs_by_status(
    status: str,
    *,
    jobs_path: str | None,
    log_level: str,
    facefusion_root: str | None,
    python_path: str | None,
) -> dict[str, Any]:
    args = ["job-list", status, "--log-level", log_level]
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])
    return _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)


def _count_job_rows(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        lowered = stripped.lower()
        if "job id" in lowered or set(stripped) <= {"|", "-", "+", " "}:
            continue
        count += 1
    return count


def _detect_default_facefusion_root() -> Path:
    env_root = os.environ.get("FACEFUSION_ROOT")
    if env_root:
        return Path(env_root)

    config_root = _read_env_config().get("facefusion_root")
    if config_root:
        return Path(config_root)

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
DEFAULT_PYTHON = Path(
    os.environ.get(
        "FACEFUSION_PYTHON",
        _read_env_config().get("python_path", FACEFUSION_ROOT / ".venv" / "Scripts" / "python.exe"),
    )
)


def _facefusion_python(facefusion_root: str | None = None, python_path: str | None = None) -> Path:
    if python_path:
        return Path(python_path)
    if os.environ.get("FACEFUSION_PYTHON"):
        return Path(os.environ["FACEFUSION_PYTHON"])
    config_python = _read_env_config().get("python_path")
    if config_python and not facefusion_root:
        return Path(config_python)
    if facefusion_root:
        return Path(facefusion_root) / ".venv" / "Scripts" / "python.exe"
    return DEFAULT_PYTHON


def _facefusion_root(facefusion_root: str | None = None) -> Path:
    if facefusion_root:
        return Path(facefusion_root)
    if os.environ.get("FACEFUSION_ROOT"):
        return Path(os.environ["FACEFUSION_ROOT"])
    config_root = _read_env_config().get("facefusion_root")
    if config_root:
        return Path(config_root)
    return FACEFUSION_ROOT


def _recommended_install_root(facefusion_root: str | None = None) -> Path:
    if facefusion_root:
        return Path(facefusion_root)
    if os.environ.get("FACEFUSION_ROOT"):
        return Path(os.environ["FACEFUSION_ROOT"])
    if (FACEFUSION_ROOT / "facefusion.py").exists():
        return FACEFUSION_ROOT
    return PLUGIN_ROOT / ".facefusion-runtime"


def _multi_actor_projects_root(project_root: str | None = None, facefusion_root: str | None = None) -> Path:
    if project_root:
        return Path(project_root)
    return _facefusion_root(facefusion_root) / ".multi-actor-projects"


def _project_dir(project_id: str, project_root: str | None = None, facefusion_root: str | None = None) -> Path:
    return _multi_actor_projects_root(project_root=project_root, facefusion_root=facefusion_root) / project_id


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _run_subprocess(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
        }
    except OSError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
        }
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


def _launch_subprocess(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
        }
    except OSError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
        }
    return {
        "command": command,
        "cwd": str(cwd),
        "pid": process.pid,
        "return_code": None,
        "stdout": "",
        "stderr": "",
        "stdout_summary": "",
        "stderr_summary": "",
        "success": True,
    }


def _launch_subprocess_background(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
            "background": True,
        }
    except OSError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "return_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "stdout_summary": "",
            "stderr_summary": str(exc),
            "success": False,
            "background": True,
        }
    return {
        "command": command,
        "cwd": str(cwd),
        "pid": process.pid,
        "return_code": None,
        "stdout": "",
        "stderr": "",
        "stdout_summary": "",
        "stderr_summary": "",
        "success": True,
        "background": True,
    }


def _build_facefusion_process_command(root: Path, python_exe: Path, command_args: list[str], skip_nsfw_check: bool) -> tuple[list[str], list[str]]:
    effective_command_args = ["facefusion.py", *command_args]
    if skip_nsfw_check:
        argv_literal = repr(effective_command_args)
        injected = (
            f"import runpy, sys; sys.path.insert(0, r'{str(root)}'); "
            "import facefusion.content_analyser as _content_analyser; "
            "_content_analyser.analyse_stream = lambda *args, **kwargs: False; "
            "_content_analyser.analyse_frame = lambda *args, **kwargs: False; "
            "_content_analyser.analyse_image = lambda *args, **kwargs: False; "
            "_content_analyser.analyse_video = lambda *args, **kwargs: False; "
            "_content_analyser.detect_nsfw = lambda *args, **kwargs: False; "
            "_content_analyser.detect_with_nsfw_1 = lambda *args, **kwargs: False; "
            "_content_analyser.detect_with_nsfw_2 = lambda *args, **kwargs: False; "
            "_content_analyser.detect_with_nsfw_3 = lambda *args, **kwargs: False; "
            f"sys.argv = {argv_literal}; "
            "runpy.run_path('facefusion.py', run_name='__main__')"
        )
        return [str(python_exe), "-c", injected], effective_command_args
    return [str(python_exe), *effective_command_args], effective_command_args


def _run_facefusion_command(
    command_args: list[str],
    facefusion_root: str | None = None,
    python_path: str | None = None,
    skip_nsfw_check: bool = False,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    command, effective_command_args = _build_facefusion_process_command(root, python_exe, command_args, skip_nsfw_check)
    result = _run_subprocess(command, root)
    result["effective_command_args"] = effective_command_args
    result["skip_nsfw_check"] = skip_nsfw_check
    return result


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


def _flat_options_to_args(values: dict[str, Any] | None, rename: dict[str, str] | None = None) -> list[str]:
    args: list[str] = []
    _append_flat_options(args, values, rename=rename)
    return args


def _merge_option_dict(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        merged[key] = value
    return merged


def _merge_list(base: list[Any] | None, override: list[Any] | None) -> list[Any]:
    if override is not None:
        return list(override)
    if base is not None:
        return list(base)
    return []


def _resolve_preset_bundle(
    preset: str | None,
    *,
    processors: list[str] | None,
    execution: dict[str, Any] | None,
    output_options: dict[str, Any] | None,
    memory_options: dict[str, Any] | None,
    face_options: dict[str, Any] | None,
    download_options: dict[str, Any] | None,
    misc_options: dict[str, Any] | None,
    extra_args: list[str] | None,
) -> dict[str, Any]:
    if not preset:
        return {
            "preset": None,
            "processors": list(processors or []),
            "execution": dict(execution or {}),
            "output_options": dict(output_options or {}),
            "memory_options": dict(memory_options or {}),
            "face_options": dict(face_options or {}),
            "download_options": dict(download_options or {}),
            "misc_options": dict(misc_options or {}),
            "extra_args": list(extra_args or []),
        }
    if preset not in PRESET_LIBRARY:
        raise ValueError(f"Unknown preset: {preset}")
    preset_payload = PRESET_LIBRARY[preset]
    return {
        "preset": preset,
        "processors": _merge_list(preset_payload.get("processors"), processors),
        "execution": _merge_option_dict(preset_payload.get("execution"), execution),
        "output_options": _merge_option_dict(preset_payload.get("output_options"), output_options),
        "memory_options": _merge_option_dict(preset_payload.get("memory_options"), memory_options),
        "face_options": _merge_option_dict(preset_payload.get("face_options"), face_options),
        "download_options": _merge_option_dict(preset_payload.get("download_options"), download_options),
        "misc_options": _merge_option_dict(preset_payload.get("misc_options"), misc_options),
        "extra_args": _merge_list(preset_payload.get("extra_args"), extra_args),
    }


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


def _command_available(command: str, cwd: Path | None = None) -> dict[str, Any]:
    return _run_subprocess([command, "--version"], cwd=cwd or PLUGIN_ROOT)


def _venv_paths(install_root: Path) -> dict[str, Path]:
    venv_root = install_root / ".venv"
    scripts_dir = venv_root / "Scripts"
    return {
        "venv_root": venv_root,
        "scripts_dir": scripts_dir,
        "python": scripts_dir / "python.exe",
        "pip": scripts_dir / "pip.exe",
    }


def _venv_env(install_root: Path) -> dict[str, str]:
    paths = _venv_paths(install_root)
    env = os.environ.copy()
    existing_path = env.get("PATH", "")
    env["PATH"] = str(paths["scripts_dir"]) + (os.pathsep + existing_path if existing_path else "")
    env["VIRTUAL_ENV"] = str(paths["venv_root"])
    return env


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


def _available_choice_catalog(facefusion_root: str | None = None, python_path: str | None = None) -> dict[str, Any]:
    result = _run_facefusion_code(
        """
import json
from pathlib import Path
import facefusion.choices as c
from facefusion.processors.modules.age_modifier import choices as age_modifier_choices
from facefusion.processors.modules.background_remover import choices as background_remover_choices
from facefusion.processors.modules.deep_swapper import choices as deep_swapper_choices
from facefusion.processors.modules.expression_restorer import choices as expression_restorer_choices
from facefusion.processors.modules.face_debugger import choices as face_debugger_choices
from facefusion.processors.modules.face_editor import choices as face_editor_choices
from facefusion.processors.modules.face_enhancer import choices as face_enhancer_choices
from facefusion.processors.modules.face_swapper import choices as face_swapper_choices
from facefusion.processors.modules.frame_colorizer import choices as frame_colorizer_choices
from facefusion.processors.modules.frame_enhancer import choices as frame_enhancer_choices
from facefusion.processors.modules.lip_syncer import choices as lip_syncer_choices
ui_layouts = sorted(
    path.stem for path in Path('facefusion/uis/layouts').glob('*.py')
    if path.stem != '__init__'
)
catalog = {
    'ui_layouts': ui_layouts,
    'ui_workflows': c.ui_workflows,
    'download_providers': c.download_providers,
    'download_scopes': c.download_scopes,
    'video_memory_strategies': c.video_memory_strategies,
    'log_levels': c.log_levels,
    'benchmark_modes': c.benchmark_modes,
    'benchmark_resolutions': c.benchmark_resolutions,
    'benchmark_cycle_count_range': list(c.benchmark_cycle_count_range),
    'execution_thread_count_range': list(c.execution_thread_count_range),
    'system_memory_limit_range': list(c.system_memory_limit_range),
    'face': {
        'detector_models': c.face_detector_models,
        'detector_sizes_by_model': c.face_detector_set,
        'detector_angles': list(c.face_detector_angles),
        'detector_score_range': list(c.face_detector_score_range),
        'detector_margin_range': list(c.face_detector_margin_range),
        'landmarker_models': c.face_landmarker_models,
        'landmarker_score_range': list(c.face_landmarker_score_range),
        'selector_modes': c.face_selector_modes,
        'selector_orders': c.face_selector_orders,
        'selector_genders': c.face_selector_genders,
        'selector_races': c.face_selector_races,
        'selector_age_range': list(c.face_selector_age_range),
        'reference_face_distance_range': list(c.reference_face_distance_range),
        'occluder_models': c.face_occluder_models,
        'parser_models': c.face_parser_models,
        'mask_types': c.face_mask_types,
        'mask_areas': c.face_mask_areas,
        'mask_regions': c.face_mask_regions,
        'mask_blur_range': list(c.face_mask_blur_range),
        'mask_padding_range': list(c.face_mask_padding_range),
        'voice_extractor_models': c.voice_extractor_models,
    },
    'output': {
        'audio_encoders': c.output_audio_encoders,
        'video_encoders': c.output_video_encoders,
        'video_presets': c.output_video_presets,
        'image_formats': c.image_formats,
        'audio_formats': c.audio_formats,
        'video_formats': c.video_formats,
        'temp_frame_formats': c.temp_frame_formats,
        'image_quality_range': list(c.output_image_quality_range),
        'image_scale_range': list(c.output_image_scale_range),
        'audio_quality_range': list(c.output_audio_quality_range),
        'audio_volume_range': list(c.output_audio_volume_range),
        'video_quality_range': list(c.output_video_quality_range),
        'video_scale_range': list(c.output_video_scale_range),
    },
    'processor_models': {
        'age_modifier_models': age_modifier_choices.age_modifier_models,
        'background_remover_models': background_remover_choices.background_remover_models,
        'deep_swapper_models': deep_swapper_choices.deep_swapper_models,
        'expression_restorer_models': expression_restorer_choices.expression_restorer_models,
        'face_debugger_items': face_debugger_choices.face_debugger_items,
        'face_editor_models': face_editor_choices.face_editor_models,
        'face_enhancer_models': face_enhancer_choices.face_enhancer_models,
        'face_swapper_models': face_swapper_choices.face_swapper_models,
        'frame_colorizer_models': frame_colorizer_choices.frame_colorizer_models,
        'frame_enhancer_models': frame_enhancer_choices.frame_enhancer_models,
        'lip_syncer_models': lip_syncer_choices.lip_syncer_models,
    },
}
print(json.dumps(catalog, ensure_ascii=False))
""",
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
    include_default_execution: bool = True,
) -> list[str]:
    args: list[str] = []
    if processors:
        args.extend(["--processors", *processors])

    normalized_execution = dict(execution or {})
    if include_default_execution and ("providers" not in normalized_execution or not normalized_execution["providers"]):
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


def _extract_skip_nsfw_check(misc_options: dict[str, Any] | None) -> tuple[dict[str, Any], bool]:
    normalized_misc = dict(misc_options or {})
    default_skip = _default_skip_nsfw_check()
    skip_nsfw_check = bool(normalized_misc.pop("skip_nsfw_check", default_skip))
    return normalized_misc, skip_nsfw_check


def _require_existing_file(path: str, field_name: str) -> None:
    if not Path(path).is_file():
        raise ValueError(f"{field_name} does not exist or is not a file: {path}")


def _ensure_output_allowed(output_path: str, output_options: dict[str, Any] | None) -> None:
    overwrite = bool((output_options or {}).get("overwrite"))
    if Path(output_path).exists() and not overwrite:
        raise ValueError(f"output_path already exists and overwrite is false: {output_path}")


def _normalize_role(role: dict[str, Any]) -> dict[str, Any]:
    source_assets = dict(role.get("source_assets") or {})
    if role.get("source_face_path"):
        source_assets["face"] = role["source_face_path"]
    if role.get("source_audio_path"):
        source_assets["audio"] = role["source_audio_path"]
    if role.get("source_image_path"):
        source_assets["image"] = role["source_image_path"]
    if role.get("source_video_path"):
        source_assets["video"] = role["source_video_path"]
    if not source_assets:
        raise ValueError("role must include at least one source asset")
    for asset_kind, asset_path in source_assets.items():
        _require_existing_file(asset_path, f"role.source_assets[{asset_kind}]")
    primary_asset = source_assets.get("face") or next(iter(source_assets.values()))
    role_id = role.get("role_id") or _slugify(role.get("role_name") or Path(primary_asset).stem)
    normalized = {
        "role_id": role_id,
        "role_name": role.get("role_name") or role_id,
        "source_face_path": source_assets.get("face"),
        "source_audio_path": source_assets.get("audio"),
        "source_assets": source_assets,
        "notes": role.get("notes", ""),
    }
    if role.get("source_image_path"):
        normalized["source_image_path"] = source_assets.get("image")
    if role.get("source_video_path"):
        normalized["source_video_path"] = source_assets.get("video")
    return normalized


def _normalize_operation(
    index: int,
    operation: dict[str, Any],
    shot_roles: list[str],
    shot_preview_required: bool,
    shot_risk_level: str,
) -> dict[str, Any]:
    operation_type = operation.get("operation_type") or "face_swap"
    if operation_type not in MULTI_ACTOR_OPERATION_PROFILES:
        raise ValueError(f"Unsupported operation_type: {operation_type}")
    profile = MULTI_ACTOR_OPERATION_PROFILES[operation_type]
    default_payload = _multi_actor_operation_defaults(operation_type)
    if "roles" in operation:
        roles = list(operation.get("roles") or [])
    elif profile["roles_required"]:
        roles = list(shot_roles)
    else:
        roles = []
    if profile["roles_required"] and not roles and not operation.get("source_paths_override"):
        raise ValueError(f"operation_type '{operation_type}' requires at least one role or source_paths_override")
    if not profile.get("supports_multi_role", True) and len(roles) > 1:
        raise ValueError(f"operation_type '{operation_type}' does not support multiple roles in one task")
    preview_required = operation.get("preview_required")
    if preview_required is None:
        preview_default = profile.get("preview_default")
        if isinstance(preview_default, bool):
            preview_required = preview_default
        else:
            preview_required = shot_preview_required
    operation_id = operation.get("operation_id")
    if not operation_id:
        role_suffix = "-".join(roles) if roles else "global"
        operation_id = f"{index:02d}-{_slugify(operation_type)}-{role_suffix}"
    normalized = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "roles": roles,
        "processors": operation.get("processors") or default_payload.get("processors"),
        "source_asset_kind": operation.get("source_asset_kind") or profile.get("source_asset_kind"),
        "source_paths_override": operation.get("source_paths_override"),
        "processor_options": _merge_option_dict(default_payload.get("processor_options"), operation.get("processor_options")),
        "face_options": _merge_option_dict(default_payload.get("face_options"), operation.get("face_options")),
        "output_options": _merge_option_dict(default_payload.get("output_options"), operation.get("output_options")),
        "misc_options": _merge_option_dict(default_payload.get("misc_options"), operation.get("misc_options")),
        "extra_args": _merge_list(default_payload.get("extra_args"), operation.get("extra_args")),
        "preview_required": bool(preview_required),
        "risk_level": operation.get("risk_level") or shot_risk_level,
        "notes": operation.get("notes", ""),
    }
    if normalized["source_paths_override"]:
        for source_index, source_path in enumerate(normalized["source_paths_override"], start=1):
            _require_existing_file(source_path, f"operation.source_paths_override[{source_index}]")
    return normalized


def _normalize_shot(index: int, shot: dict[str, Any], auto_preview_policy: str) -> dict[str, Any]:
    roles = shot.get("roles") or []
    risk_level = shot.get("risk_level")
    if not risk_level:
        if len(roles) > 1:
            risk_level = "high"
        elif len(roles) == 1:
            risk_level = "low"
        else:
            risk_level = "medium"
    preview_required = shot.get("preview_required")
    if preview_required is None:
        if auto_preview_policy == "always":
            preview_required = True
        elif auto_preview_policy == "never":
            preview_required = False
        else:
            preview_required = risk_level in {"medium", "high"} or len(roles) > 1
    shot_id = shot.get("shot_id") or f"s{index:03d}"
    normalized = {
        "shot_id": shot_id,
        "target_path": shot["target_path"],
        "trim_start": shot.get("trim_start"),
        "trim_end": shot.get("trim_end"),
        "frame_start": shot.get("frame_start"),
        "frame_end": shot.get("frame_end"),
        "roles": roles,
        "preview_required": bool(preview_required),
        "risk_level": risk_level,
        "notes": shot.get("notes", ""),
    }
    operations = shot.get("operations")
    if operations:
        normalized["operations"] = [
            _normalize_operation(operation_index, operation, roles, bool(preview_required), risk_level)
            for operation_index, operation in enumerate(operations, start=1)
        ]
    elif roles:
        normalized["operations"] = [
            _normalize_operation(
                1,
                {"operation_type": "face_swap", "roles": roles, "preview_required": preview_required},
                roles,
                bool(preview_required),
                risk_level,
            )
        ]
    else:
        normalized["operations"] = []
    _require_existing_file(normalized["target_path"], "shot.target_path")
    return normalized


def _task_output_path(project_dir: Path, task_type: str, shot_id: str, operation_id: str, operation_type: str, target_path: str) -> str:
    folder = "previews" if task_type == "preview" else "renders"
    suffix = Path(target_path).suffix or ".mp4"
    return str(project_dir / folder / f"{shot_id}-{_slugify(operation_id)}-{_slugify(operation_type)}-{task_type}{suffix}")


def _shot_operation_decision_to_operations(
    shot: dict[str, Any],
    enabled_operations: list[str],
) -> list[dict[str, Any]]:
    roles = list(shot.get("roles") or [])
    preview_required = bool(shot.get("preview_required"))
    risk_level = shot.get("risk_level") or "medium"
    operations: list[dict[str, Any]] = []
    if roles:
        operations.append(
            _normalize_operation(
                1,
                {"operation_type": "face_swap", "roles": roles, "preview_required": preview_required},
                roles,
                preview_required,
                risk_level,
            )
        )
    next_index = len(operations) + 1
    for operation_type in enabled_operations:
        if operation_type == "face_swap":
            continue
        if operation_type not in MULTI_ACTOR_OPERATION_PROFILES:
            raise ValueError(f"Unsupported operation_type in shot decision: {operation_type}")
        if operation_type == "lip_sync":
            if not roles:
                continue
            for role_id in roles:
                operations.append(
                    _normalize_operation(
                        next_index,
                        {
                            "operation_type": "lip_sync",
                            "roles": [role_id],
                            "preview_required": True,
                        },
                        roles,
                        preview_required,
                        risk_level,
                    )
                )
                next_index += 1
            continue
        operations.append(
            _normalize_operation(
                next_index,
                {
                    "operation_type": operation_type,
                    "preview_required": preview_required,
                },
                roles,
                preview_required,
                risk_level,
            )
        )
        next_index += 1
    return operations


def _apply_default_shot_operations_to_shot(shot: dict[str, Any]) -> None:
    default_operations = _default_shot_operations()
    if not default_operations:
        return
    current_non_swap = [
        operation.get("operation_type")
        for operation in (shot.get("operations") or [])
        if operation.get("operation_type") != "face_swap"
    ]
    if current_non_swap:
        return
    shot["operations"] = _shot_operation_decision_to_operations(shot, default_operations)


def _coerce_frame_bound(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Frame bounds cannot be boolean values")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(float(str(value)))


def _job_step_output_path(job_id: str, step_index: int, output_path: str) -> str:
    output_file_path = Path(output_path)
    return str(output_file_path.with_name(f"{output_file_path.stem}-{job_id}-{step_index}{output_file_path.suffix}"))


def _run_multi_actor_verifier(
    job_id: str,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any] | None:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    verifier_script = PLUGIN_ROOT / "scripts" / "multi_actor_verify.py"
    if not verifier_script.exists():
        return None
    completed = _run_subprocess(
        [
            str(python_exe),
            str(verifier_script),
            "--facefusion-root",
            str(root),
            "--job-id",
            job_id,
        ],
        cwd=root,
    )
    payload = {
        "success": completed["success"],
        "command": completed["command"],
        "cwd": completed["cwd"],
        "stdout_summary": completed["stdout_summary"],
        "stderr_summary": completed["stderr_summary"],
    }
    try:
        parsed = json.loads(completed["stdout"]) if completed.get("stdout") else {}
    except json.JSONDecodeError:
        parsed = {}
    payload["result"] = parsed
    return payload


def _run_reference_discovery(
    project_id: str,
    sample_frames_per_shot: int = 2,
    cluster_distance_threshold: float = 0.35,
    source_hint_names: list[str] | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    script_path = PLUGIN_ROOT / "scripts" / "reference_discovery.py"
    command = [
        str(python_exe),
        str(script_path),
        "--facefusion-root",
        str(root),
        "--project-id",
        project_id,
        "--sample-frames-per-shot",
        str(sample_frames_per_shot),
        "--cluster-distance-threshold",
        str(cluster_distance_threshold),
    ]
    if source_hint_names:
        command.extend(["--source-hint-names", *source_hint_names])
    result = _run_subprocess(command, root)
    payload = {
        **result,
        "project_id": project_id,
        "sample_frames_per_shot": sample_frames_per_shot,
        "cluster_distance_threshold": cluster_distance_threshold,
        "source_hint_names": source_hint_names or [],
    }
    payload["result"] = _parse_json_stdout(result, {})
    return payload


def _build_task_step_requests(
    task: dict[str, Any],
    shot: dict[str, Any],
    roles_by_id: dict[str, dict[str, Any]],
    project_dir: Path,
    job_id: str,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    source_paths = list(task.get("source_paths") or [])
    if not source_paths:
        source_asset_kind = task.get("source_asset_kind")
        if source_asset_kind:
            for role_id in task["roles"]:
                role = roles_by_id[role_id]
                source_asset_path = (role.get("source_assets") or {}).get(source_asset_kind)
                if not source_asset_path:
                    raise ValueError(f"Role '{role_id}' is missing source asset kind '{source_asset_kind}'")
                source_paths.append(source_asset_path)
    face_options: dict[str, Any] = dict(task.get("face_options") or {})
    if task["mode"] == "reference":
        face_options["face_selector_mode"] = "reference"
    if shot.get("trim_start") is not None:
        face_options["trim_frame_start"] = _coerce_frame_bound(shot["trim_start"])
    if shot.get("trim_end") is not None:
        face_options["trim_frame_end"] = _coerce_frame_bound(shot["trim_end"])
    if shot.get("frame_start") is not None:
        face_options["trim_frame_start"] = _coerce_frame_bound(shot["frame_start"])
    if shot.get("frame_end") is not None:
        face_options["trim_frame_end"] = _coerce_frame_bound(shot["frame_end"])
    extra_args = list(task.get("extra_args") or [])
    extra_args.extend(_flat_options_to_args(task.get("processor_options")))
    base_request = {
        "processors": task["processors"],
        "output_options": {"overwrite": overwrite},
        "face_options": face_options,
        "extra_args": extra_args,
    }
    can_chain_multi_role_swap = (
        task.get("operation_type") == "face_swap"
        and task.get("mode") == "reference"
        and len(task.get("roles") or []) > 1
        and len(source_paths) == len(task["roles"])
    )
    if not can_chain_multi_role_swap:
        return [
            {
                **base_request,
                "source_paths": source_paths,
                "target_path": shot["target_path"],
                "output_path": task["output_path"],
            }
        ]

    intermediate_dir = project_dir / "manifests" / "intermediate"
    _ensure_directory(intermediate_dir)
    selector_order = face_options.get("face_selector_order") or "left-right"
    current_target_path = shot["target_path"]
    step_requests: list[dict[str, Any]] = []
    output_suffix = Path(task["output_path"]).suffix or ".mp4"
    for role_index, (role_id, role_source_path) in enumerate(zip(task["roles"], source_paths)):
        role_face_options = dict(face_options)
        role_face_options["face_selector_mode"] = "reference"
        role_face_options["face_selector_order"] = selector_order
        role_face_options["reference_face_position"] = role_index
        is_last_step = role_index == len(task["roles"]) - 1
        if is_last_step:
            step_output_path = task["output_path"]
        else:
            step_output_path = str(intermediate_dir / f"{task['task_id']}-{role_id}-step-{role_index + 1}{output_suffix}")
        step_requests.append(
            {
                **base_request,
                "role_id": role_id,
                "source_paths": [role_source_path],
                "target_path": current_target_path,
                "output_path": step_output_path,
                "face_options": role_face_options,
            }
        )
        current_target_path = _job_step_output_path(job_id, role_index, step_output_path)
    return step_requests


def _set_task_status(
    task: dict[str, Any],
    status: str,
    note: str | None = None,
    **extra: Any,
) -> None:
    task["status"] = status
    if note is not None:
        task["status_note"] = note
    task.update(extra)


def _find_task(plan: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in plan["tasks"]:
        if task["task_id"] == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")


def _create_auto_job_id(prefix: str, target_path: str) -> str:
    target_slug = _slugify(Path(target_path).stem or "target")
    return f"{prefix}-{target_slug}-{int(time.time() * 1000)}"


def _queue_single_step_job(
    *,
    job_prefix: str,
    target_path: str,
    step_request: dict[str, Any],
    jobs_path: str | None,
    log_level: str,
    facefusion_root: str | None,
    python_path: str | None,
) -> dict[str, Any]:
    job_id = _create_auto_job_id(job_prefix, target_path)
    create_result = facefusion_create_job(
        job_id=job_id,
        jobs_path=jobs_path,
        log_level=log_level,
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    if not create_result["success"]:
        return {
            "success": False,
            "queued": False,
            "job_id": job_id,
            "create_result": create_result,
        }
    add_result = facefusion_update_job_steps(
        action="add",
        job_id=job_id,
        step_request=step_request,
        jobs_path=jobs_path,
        log_level=log_level,
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    if not add_result["success"]:
        return {
            "success": False,
            "queued": False,
            "job_id": job_id,
            "create_result": create_result,
            "add_result": add_result,
        }
    submit_result = facefusion_run_jobs(
        mode="submit",
        job_id=job_id,
        jobs_path=jobs_path,
        log_level=log_level,
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    background_result = None
    if submit_result["success"] and _default_background_queue_runner():
        background_result = _ensure_queue_worker(
            jobs_path=jobs_path,
            log_level=log_level,
            skip_nsfw_check=None,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
    return {
        "success": submit_result["success"],
        "queued": submit_result["success"],
        "job_id": job_id,
        "create_result": create_result,
        "add_result": add_result,
        "submit_result": submit_result,
        "background_runner_result": background_result,
        "background_started": bool(background_result and background_result.get("success")),
    }


def _run_task_shortcut(
    *,
    task_kind: str,
    source_paths: list[str],
    target_path: str,
    output_path: str,
    preset: str | None,
    default_processors: list[str],
    execution: dict[str, Any] | None,
    output_options: dict[str, Any] | None,
    memory_options: dict[str, Any] | None,
    face_options: dict[str, Any] | None,
    download_options: dict[str, Any] | None,
    misc_options: dict[str, Any] | None,
    extra_args: list[str] | None,
    facefusion_root: str | None,
    python_path: str | None,
) -> dict[str, Any]:
    resolved, effective_preset = _resolve_runtime_bundle(
        preset,
        defaults_bucket="task_defaults",
        defaults_name=task_kind,
        fallback_processors=default_processors,
        processors=None,
        execution=execution,
        output_options=output_options,
        memory_options=memory_options,
        face_options=face_options,
        download_options=download_options,
        misc_options=misc_options,
        extra_args=extra_args,
    )
    return facefusion_run_job(
        source_paths=source_paths,
        target_path=target_path,
        output_path=output_path,
        preset=effective_preset,
        processors=resolved["processors"],
        execution=resolved["execution"],
        output_options=resolved["output_options"],
        memory_options=resolved["memory_options"],
        face_options=resolved["face_options"],
        download_options=resolved["download_options"],
        misc_options=resolved["misc_options"],
        extra_args=resolved["extra_args"],
        facefusion_root=facefusion_root,
        python_path=python_path,
    )


def _launch_facefusion_background_job(
    *,
    mode: str,
    job_id: str | None,
    jobs_path: str | None,
    halt_on_error: bool,
    log_level: str,
    skip_nsfw_check: bool,
    facefusion_root: str | None,
    python_path: str | None,
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
    args = [mode_map[mode]]
    if job_id:
        args.append(job_id)
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])
    if halt_on_error:
        args.append("--halt-on-error")
    args.extend(["--log-level", log_level])
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    command, effective_command_args = _build_facefusion_process_command(root, python_exe, args, skip_nsfw_check)
    result = _launch_subprocess_background(command, root)
    result["effective_command_args"] = effective_command_args
    result["skip_nsfw_check"] = skip_nsfw_check
    result["mode"] = mode
    result["job_id"] = job_id
    return result


def _ensure_queue_worker(
    *,
    jobs_path: str | None,
    log_level: str,
    skip_nsfw_check: bool | None,
    facefusion_root: str | None,
    python_path: str | None,
) -> dict[str, Any]:
    active_state = _get_active_runner_state()
    if active_state:
        return {
            "success": True,
            "reused": True,
            "background": True,
            "pid": active_state.get("pid"),
            "state_path": str(RUNNER_STATE_PATH),
            "runner_state": active_state,
        }
    resolved_skip_nsfw_check = _default_skip_nsfw_check() if skip_nsfw_check is None else skip_nsfw_check
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    worker_script = PLUGIN_ROOT / "scripts" / "queue_worker.py"
    command = [
        str(python_exe),
        str(worker_script),
        "--facefusion-root",
        str(root),
        "--python-path",
        str(python_exe),
        "--state-path",
        str(RUNNER_STATE_PATH),
        "--log-level",
        log_level,
    ]
    if jobs_path:
        command.extend(["--jobs-path", jobs_path])
    if resolved_skip_nsfw_check:
        command.append("--skip-nsfw-check")
    result = _launch_subprocess_background(command, root)
    if result.get("success"):
        _write_runner_state(
            {
                "started_at": time.time(),
                "facefusion_root": str(root),
                "jobs_path": jobs_path,
                "status": "starting",
            }
        )
    result["state_path"] = str(RUNNER_STATE_PATH)
    result["reused"] = False
    result["skip_nsfw_check"] = resolved_skip_nsfw_check
    return result


def _build_plan_view_model(
    cast: dict[str, Any],
    shots: dict[str, Any],
    plan: dict[str, Any],
    references: dict[str, Any] | None = None,
) -> dict[str, Any]:
    roles = cast.get("roles") or []
    role_names = {role["role_id"]: role.get("role_name") or role["role_id"] for role in roles}
    shot_list = shots.get("shots") or []
    tasks = plan.get("tasks") or []
    shots_by_id = {shot["shot_id"]: shot for shot in shot_list}
    status_counts: dict[str, int] = {}
    operation_counts: dict[str, int] = {}
    preview_count = 0
    final_count = 0
    task_cards = []
    for task in tasks:
        status = task.get("status") or "unknown"
        operation_type = task.get("operation_type") or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        operation_counts[operation_type] = operation_counts.get(operation_type, 0) + 1
        if task.get("task_type") == "preview":
            preview_count += 1
        if task.get("task_type") == "final":
            final_count += 1
        shot = shots_by_id.get(task["shot_id"], {})
        task_cards.append(
            {
                "task_id": task["task_id"],
                "task_type": task.get("task_type"),
                "status": status,
                "shot_id": task["shot_id"],
                "operation_id": task.get("operation_id"),
                "operation_type": operation_type,
                "roles": task.get("roles") or [],
                "role_names": [role_names.get(role_id, role_id) for role_id in task.get("roles") or []],
                "processors": task.get("processors") or [],
                "mode": task.get("mode"),
                "risk_level": task.get("risk_level"),
                "quality_profile": task.get("quality_profile"),
                "execution_provider": task.get("execution_provider"),
                "output_path": task.get("output_path"),
                "status_note": task.get("status_note", ""),
                "trim_start": shot.get("trim_start"),
                "trim_end": shot.get("trim_end"),
                "frame_start": shot.get("frame_start"),
                "frame_end": shot.get("frame_end"),
                "preview_required": any(
                    operation.get("operation_id") == task.get("operation_id") and operation.get("preview_required")
                    for operation in shot.get("operations") or []
                ),
                "shot_notes": shot.get("notes", ""),
            }
        )
    return {
        "project_id": plan.get("project_id") or cast.get("project_id") or shots.get("project_id"),
        "summary": {
            "role_count": len(roles),
            "shot_count": len(shot_list),
            "task_count": len(tasks),
            "preview_count": preview_count,
            "final_count": final_count,
            "status_counts": status_counts,
            "operation_counts": operation_counts,
            "reference_cluster_count": len((references or {}).get("clusters") or []),
        },
        "roles": roles,
        "shots": shot_list,
        "tasks": task_cards,
        "references": references or {},
    }


def _build_multi_actor_confirmation_summary(
    project_id: str,
    project_dir: Path,
    cast: dict[str, Any],
    shots: dict[str, Any],
    references: dict[str, Any] | None,
    plan: dict[str, Any] | None,
) -> dict[str, Any]:
    roles = cast.get("roles") or []
    shot_list = shots.get("shots") or []
    decision_groups = (references or {}).get("decision_groups") or []
    tasks = (plan or {}).get("tasks") or []
    role_names = {role["role_id"]: role.get("role_name") or role["role_id"] for role in roles}
    unresolved_roles = []
    for role in roles:
        source_face_path = role.get("source_face_path") or (role.get("source_assets") or {}).get("face")
        if not source_face_path:
            unresolved_roles.append(role["role_id"])

    shot_summaries = []
    for shot in shot_list:
        operations = shot.get("operations") or []
        shot_summaries.append(
            {
                "shot_id": shot["shot_id"],
                "target_path": shot["target_path"],
                "frame_start": shot.get("frame_start"),
                "frame_end": shot.get("frame_end"),
                "trim_start": shot.get("trim_start"),
                "trim_end": shot.get("trim_end"),
                "roles": list(shot.get("roles") or []),
                "role_names": [role_names.get(role_id, role_id) for role_id in (shot.get("roles") or [])],
                "preview_required": bool(shot.get("preview_required")),
                "risk_level": shot.get("risk_level"),
                "notes": shot.get("notes", ""),
                "operations": [
                    {
                        "operation_id": operation.get("operation_id"),
                        "operation_type": operation.get("operation_type"),
                        "roles": list(operation.get("roles") or []),
                        "processors": list(operation.get("processors") or []),
                        "processor_options": operation.get("processor_options") or {},
                        "face_options": operation.get("face_options") or {},
                        "output_options": operation.get("output_options") or {},
                        "misc_options": operation.get("misc_options") or {},
                        "extra_args": list(operation.get("extra_args") or []),
                    }
                    for operation in operations
                ],
            }
        )

    task_counts = {
        "preview": len([task for task in tasks if task.get("task_type") == "preview"]),
        "final": len([task for task in tasks if task.get("task_type") == "final"]),
    }
    task_status_counts: dict[str, int] = {}
    for task in tasks:
        status = task.get("status") or "unknown"
        task_status_counts[status] = task_status_counts.get(status, 0) + 1

    ready_for_execution = bool(tasks) and not unresolved_roles
    return {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "cast_path": str(project_dir / "cast.json"),
        "shots_path": str(project_dir / "shots.json"),
        "references_path": str(project_dir / "references.json") if references is not None else None,
        "plan_path": str(project_dir / "plan.json") if plan is not None else None,
        "roles": [
            {
                "role_id": role["role_id"],
                "role_name": role.get("role_name") or role["role_id"],
                "source_face_path": role.get("source_face_path"),
                "source_audio_path": role.get("source_audio_path"),
                "source_assets": role.get("source_assets") or {},
                "notes": role.get("notes", ""),
            }
            for role in roles
        ],
        "decision_groups": [
            {
                "group_id": group.get("group_id"),
                "cluster_ids": list(group.get("cluster_ids") or []),
                "role_id": group.get("role_id"),
                "role_name": group.get("role_name"),
                "source_path": (group.get("source_candidate") or {}).get("source_path"),
            }
            for group in decision_groups
        ],
        "shots": shot_summaries,
        "plan_overview": {
            "preview_mode": (plan or {}).get("preview_mode"),
            "quality_profile": (plan or {}).get("quality_profile"),
            "task_counts": task_counts,
            "task_status_counts": task_status_counts,
        } if plan is not None else None,
        "unresolved_roles": unresolved_roles,
        "ready_for_execution": ready_for_execution,
        "confirmation_required_before_materialize": True,
    }


def _render_plan_html(plan_view: dict[str, Any]) -> str:
    payload = json.dumps(plan_view, ensure_ascii=False)
    title = html.escape(f"FaceFusion Plan - {plan_view['project_id']}")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f3ea;
      --panel: rgba(255, 255, 255, 0.82);
      --panel-strong: #fffdf8;
      --ink: #1f1d1a;
      --muted: #6e655d;
      --accent: #b14d24;
      --accent-soft: rgba(177, 77, 36, 0.12);
      --line: rgba(61, 49, 41, 0.12);
      --ok: #2f7d4b;
      --warn: #a36911;
      --bad: #9f2d2d;
      --shadow: 0 18px 40px rgba(69, 45, 24, 0.08);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(203, 124, 72, 0.2), transparent 28rem),
        radial-gradient(circle at top right, rgba(77, 111, 142, 0.18), transparent 24rem),
        linear-gradient(180deg, #fbf8f0 0%, #f2ede3 100%);
    }}
    .shell {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      gap: 16px;
      margin-bottom: 24px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(255,247,239,0.9));
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1;
    }}
    .sub {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      max-width: 760px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
    }}
    .stat, .panel {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel);
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow);
    }}
    .stat {{
      padding: 16px 18px;
    }}
    .stat .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .stat .value {{
      margin-top: 8px;
      font-size: 28px;
      font-weight: 700;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 20px;
    }}
    .stack {{
      display: grid;
      gap: 20px;
      align-content: start;
    }}
    .panel {{
      padding: 18px;
    }}
    .panel h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .list {{
      display: grid;
      gap: 10px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
    }}
    .role, .shot {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel-strong);
    }}
    .role strong, .shot strong {{
      display: block;
      margin-bottom: 4px;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
    }}
    .toolbar input, .toolbar select {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(255,255,255,0.88);
      color: var(--ink);
      min-width: 180px;
    }}
    .tasks {{
      display: grid;
      gap: 14px;
    }}
    .task {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(248,242,234,0.94));
      box-shadow: var(--shadow);
    }}
    .task-top {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
    }}
    .task h3 {{
      margin: 0 0 8px;
      font-size: 20px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0 0;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      background: rgba(61, 49, 41, 0.08);
    }}
    .status-planned, .status-materialized, .status-approved {{ color: var(--ok); }}
    .status-blocked_on_preview, .status-blocked_on_revision, .status-rejected {{ color: var(--warn); }}
    .status-failed, .status-materialize_failed {{ color: var(--bad); }}
    .grid {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }}
    .fact {{
      padding: 12px;
      border-radius: 14px;
      background: rgba(255,255,255,0.76);
      border: 1px solid var(--line);
    }}
    .fact .k {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .fact .v {{
      margin-top: 6px;
      font-size: 14px;
      word-break: break-word;
    }}
    .empty {{
      padding: 24px;
      border: 1px dashed var(--line);
      border-radius: 18px;
      color: var(--muted);
      text-align: center;
      background: rgba(255,255,255,0.5);
    }}
    @media (max-width: 960px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">FaceFusion Multi-Actor Plan</div>
      <h1>{title}</h1>
      <p class="sub">A lightweight visual layer over <code>cast.json</code>, <code>shots.json</code>, and <code>plan.json</code> so an agent or operator can review the queue before preview approval or final renders.</p>
      <div class="stats" id="stats"></div>
    </section>
    <section class="layout">
      <aside class="stack">
        <div class="panel">
          <h2>Cast</h2>
          <div class="list" id="roles"></div>
        </div>
        <div class="panel">
          <h2>Shots</h2>
          <div class="list" id="shots"></div>
        </div>
        <div class="panel">
          <h2>References</h2>
          <div class="list" id="references"></div>
        </div>
      </aside>
      <main class="panel">
        <div class="toolbar">
          <input id="search" type="search" placeholder="Filter by role, shot, task, or processor">
          <select id="statusFilter">
            <option value="">All statuses</option>
          </select>
          <select id="typeFilter">
            <option value="">All task types</option>
            <option value="preview">Preview</option>
            <option value="final">Final</option>
          </select>
        </div>
        <div class="tasks" id="tasks"></div>
      </main>
    </section>
  </div>
  <script>
    const planView = {payload};

    const statusClass = (status) => "status-" + String(status || "unknown").replace(/[^a-z0-9_]+/gi, "_");
    const el = (tag, className, text) => {{
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }};
    const fmt = (value) => {{
      if (value === null || value === undefined || value === "") return "n/a";
      if (Array.isArray(value)) return value.length ? value.join(", ") : "n/a";
      return String(value);
    }};

    function renderStats(summary) {{
      const stats = document.getElementById("stats");
      stats.innerHTML = "";
      [
        ["Roles", summary.role_count],
        ["Shots", summary.shot_count],
        ["Tasks", summary.task_count],
        ["Previews", summary.preview_count],
        ["Finals", summary.final_count],
        ["Ref Clusters", summary.reference_cluster_count || 0]
      ].forEach(([label, value]) => {{
        const card = el("div", "stat");
        card.appendChild(el("div", "label", label));
        card.appendChild(el("div", "value", String(value)));
        stats.appendChild(card);
      }});
    }}

    function renderRoles(roles) {{
      const root = document.getElementById("roles");
      root.innerHTML = "";
      roles.forEach((role) => {{
        const card = el("div", "role");
        card.appendChild(el("strong", "", role.role_name || role.role_id));
        card.appendChild(el("div", "muted", role.role_id));
        const chips = el("div", "meta");
        Object.keys(role.source_assets || {{}}).forEach((kind) => {{
          chips.appendChild(el("span", "chip", kind));
        }});
        card.appendChild(chips);
        if (role.notes) {{
          card.appendChild(el("p", "muted", role.notes));
        }}
        root.appendChild(card);
      }});
    }}

    function renderShots(shots) {{
      const root = document.getElementById("shots");
      root.innerHTML = "";
      shots.forEach((shot) => {{
        const card = el("div", "shot");
        card.appendChild(el("strong", "", shot.shot_id));
        const detail = [shot.target_path, shot.trim_start ?? shot.frame_start, shot.trim_end ?? shot.frame_end].filter((v) => v !== undefined && v !== null);
        card.appendChild(el("div", "muted", detail.join(" | ")));
        const chips = el("div", "meta");
        (shot.roles || []).forEach((roleId) => chips.appendChild(el("span", "chip", roleId)));
        (shot.operations || []).forEach((op) => chips.appendChild(el("span", "badge", op.operation_type)));
        card.appendChild(chips);
        root.appendChild(card);
      }});
    }}

    function renderReferences(referenceState) {{
      const root = document.getElementById("references");
      root.innerHTML = "";
      const clusters = referenceState?.clusters || [];
      const groups = referenceState?.decision_groups || referenceState?.suggested_groups || [];
      if (!clusters.length) {{
        root.appendChild(el("div", "empty", "No reference discovery data yet."));
        return;
      }}
      clusters.forEach((cluster) => {{
        const card = el("div", "role");
        card.appendChild(el("strong", "", cluster.suggested_role_name || cluster.label || cluster.cluster_id));
        card.appendChild(el("div", "muted", `${{cluster.cluster_id}} | samples: ${{cluster.sample_count || 0}} | shots: ${{(cluster.shot_ids || []).join(", ") || "n/a"}}`));
        if (cluster.prefill_source_candidate) {{
          const prefill = cluster.prefill_source_candidate;
          card.appendChild(el("div", "muted", `Prefill: ${{prefill.label}}${{prefill.source_path ? " -> " + prefill.source_path : ""}}`));
        }}
        root.appendChild(card);
      }});
      if (groups.length) {{
        const foot = el("div", "muted", `Merge groups prepared: ${{groups.length}}`);
        root.appendChild(foot);
      }}
    }}

    function populateStatusFilter(tasks) {{
      const select = document.getElementById("statusFilter");
      const statuses = Array.from(new Set(tasks.map((task) => task.status))).sort();
      statuses.forEach((status) => {{
        const option = document.createElement("option");
        option.value = status;
        option.textContent = status;
        select.appendChild(option);
      }});
    }}

    function renderTasks() {{
      const search = document.getElementById("search").value.trim().toLowerCase();
      const statusFilter = document.getElementById("statusFilter").value;
      const typeFilter = document.getElementById("typeFilter").value;
      const root = document.getElementById("tasks");
      root.innerHTML = "";
      const filtered = planView.tasks.filter((task) => {{
        const haystack = [
          task.task_id,
          task.shot_id,
          task.operation_type,
          ...(task.role_names || []),
          ...(task.roles || []),
          ...(task.processors || [])
        ].join(" ").toLowerCase();
        if (search && !haystack.includes(search)) return false;
        if (statusFilter && task.status !== statusFilter) return false;
        if (typeFilter && task.task_type !== typeFilter) return false;
        return true;
      }});
      if (!filtered.length) {{
        root.appendChild(el("div", "empty", "No tasks match the current filter."));
        return;
      }}
      filtered.forEach((task) => {{
        const card = el("article", "task");
        const top = el("div", "task-top");
        const left = el("div");
        left.appendChild(el("h3", "", task.task_id));
        left.appendChild(el("div", "muted", `${{task.operation_type}} on ${{task.shot_id}}`));
        const meta = el("div", "meta");
        meta.appendChild(el("span", "badge " + statusClass(task.status), task.status));
        meta.appendChild(el("span", "badge", task.task_type));
        meta.appendChild(el("span", "badge", task.mode || "standard"));
        meta.appendChild(el("span", "badge", task.execution_provider || "provider:n/a"));
        meta.appendChild(el("span", "badge", task.risk_level || "risk:n/a"));
        left.appendChild(meta);
        top.appendChild(left);
        const roleBox = el("div", "muted", fmt(task.role_names));
        top.appendChild(roleBox);
        card.appendChild(top);
        const grid = el("div", "grid");
        [
          ["Processors", fmt(task.processors)],
          ["Output", fmt(task.output_path)],
          ["Quality", fmt(task.quality_profile)],
          ["Preview Required", task.preview_required ? "yes" : "no"],
          ["Trim Range", fmt([task.trim_start, task.trim_end].filter((v) => v !== null && v !== undefined))],
          ["Frame Range", fmt([task.frame_start, task.frame_end].filter((v) => v !== null && v !== undefined))]
        ].forEach(([key, value]) => {{
          const fact = el("div", "fact");
          fact.appendChild(el("div", "k", key));
          fact.appendChild(el("div", "v", value));
          grid.appendChild(fact);
        }});
        card.appendChild(grid);
        if (task.status_note || task.shot_notes) {{
          const note = el("p", "muted", [task.status_note, task.shot_notes].filter(Boolean).join(" | "));
          card.appendChild(note);
        }}
        root.appendChild(card);
      }});
    }}

    renderStats(planView.summary);
    renderRoles(planView.roles);
    renderShots(planView.shots);
    renderReferences(planView.references || {{}});
    populateStatusFilter(planView.tasks);
    renderTasks();

    document.getElementById("search").addEventListener("input", renderTasks);
    document.getElementById("statusFilter").addEventListener("change", renderTasks);
    document.getElementById("typeFilter").addEventListener("change", renderTasks);
  </script>
</body>
</html>
"""


def _render_reference_html(reference_view: dict[str, Any]) -> str:
    payload = json.dumps(reference_view, ensure_ascii=False)
    title = html.escape(f"FaceFusion References - {reference_view['project_id']}")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f6f3ea;
      --panel: rgba(255,255,255,0.92);
      --line: rgba(61,49,41,0.12);
      --ink: #1f1d1a;
      --muted: #6e655d;
      --accent: #b14d24;
      --accent-soft: rgba(177,77,36,0.12);
      --ok: #2d7a55;
      --warn: #9d5a14;
      --shadow: 0 18px 40px rgba(69,45,24,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", sans-serif; color: var(--ink); background: linear-gradient(180deg, #fbf8f0 0%, #f2ede3 100%); }}
    .shell {{ max-width: 1480px; margin: 0 auto; padding: 28px 20px 40px; }}
    .hero, .card {{ border: 1px solid var(--line); border-radius: 24px; background: var(--panel); box-shadow: var(--shadow); }}
    .hero {{ padding: 24px; margin-bottom: 20px; }}
    .eyebrow {{ color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }}
    h1 {{ margin: 8px 0 0; font-size: 38px; }}
    h2 {{ margin: 0 0 10px; font-size: 22px; }}
    h3 {{ margin: 0; font-size: 18px; }}
    .sub, .muted {{ color: var(--muted); }}
    .stats, .grid, .samples, .columns, .editor-grid, .facts {{ display: grid; gap: 12px; }}
    .stats {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-top: 16px; }}
    .grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
    .columns {{ grid-template-columns: minmax(0, 1.3fr) minmax(360px, 0.9fr); align-items: start; }}
    .editor-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .facts {{ grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }}
    .samples {{ grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); margin-top: 12px; }}
    .stat, .card {{ padding: 18px; }}
    .stat {{ border: 1px solid var(--line); border-radius: 16px; background: rgba(255,255,255,0.88); }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .value {{ margin-top: 8px; font-size: 26px; font-weight: 700; }}
    .samples img {{ width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 14px; border: 1px solid var(--line); background: #eee7dc; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 0; }}
    .chip {{ display: inline-flex; padding: 6px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 700; margin: 6px 6px 0 0; }}
    .chip.ok {{ background: rgba(45,122,85,0.12); color: var(--ok); }}
    .chip.warn {{ background: rgba(157,90,20,0.14); color: var(--warn); }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .button {{
      appearance: none;
      border: 1px solid rgba(177,77,36,0.24);
      background: white;
      color: var(--ink);
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
    }}
    .button.primary {{ background: var(--accent); color: white; border-color: var(--accent); }}
    .button.subtle {{ background: rgba(255,255,255,0.7); }}
    .button.danger {{ border-color: rgba(139,57,24,0.22); color: #8b3918; }}
    .stack {{ display: grid; gap: 14px; }}
    .group-card {{ padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: rgba(255,255,255,0.76); }}
    .group-card.drop-target {{ border-color: rgba(177,77,36,0.55); box-shadow: 0 0 0 3px rgba(177,77,36,0.10); }}
    .group-header {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 14px; }}
    .cluster-picker {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }}
    .cluster-option {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255,255,255,0.72);
    }}
    .cluster-option.active {{ border-color: rgba(177,77,36,0.4); background: rgba(177,77,36,0.06); }}
    .cluster-option.dragging {{ opacity: 0.55; }}
    .cluster-thumb {{ width: 100%; aspect-ratio: 1 / 1; border-radius: 12px; border: 1px solid var(--line); object-fit: cover; background: #eee7dc; }}
    .cluster-bucket {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 10px; min-height: 18px; }}
    .cluster-token {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.88);
      cursor: grab;
    }}
    .cluster-token img {{ width: 24px; height: 24px; border-radius: 999px; object-fit: cover; border: 1px solid var(--line); }}
    .field {{ display: grid; gap: 6px; }}
    .field label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; }}
    input[type="text"], select, textarea {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
      color: var(--ink);
      background: rgba(255,255,255,0.92);
    }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .raw-editor {{ min-height: 540px; font-family: Consolas, "SFMono-Regular", monospace; font-size: 12px; }}
    .notice {{
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(177,77,36,0.08);
      color: var(--muted);
      border: 1px solid var(--line);
    }}
    .notice.error {{ background: rgba(161,61,24,0.08); color: #8b3918; }}
    .facts .fact {{ padding: 12px; border-radius: 14px; background: rgba(255,255,255,0.72); border: 1px solid var(--line); }}
    .facts .fact .k {{ font-size: 12px; color: var(--muted); text-transform: uppercase; }}
    .facts .fact .v {{ margin-top: 8px; font-weight: 600; word-break: break-word; }}
    .catalog {{ display: grid; gap: 10px; }}
    .catalog-item {{ padding: 12px; border: 1px solid var(--line); border-radius: 14px; background: rgba(255,255,255,0.72); }}
    .catalog-item img {{ width: 56px; height: 56px; border-radius: 14px; object-fit: cover; border: 1px solid var(--line); margin-bottom: 8px; }}
    .shot-op-card {{ padding: 14px; border: 1px solid var(--line); border-radius: 16px; background: rgba(255,255,255,0.76); }}
    .op-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 10px; }}
    .op-toggle {{ display: flex; gap: 8px; align-items: flex-start; padding: 10px; border: 1px solid var(--line); border-radius: 14px; background: rgba(255,255,255,0.78); }}
    .op-toggle input {{ margin-top: 3px; }}
    .default-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .checkbox-stack {{ display: grid; gap: 8px; }}
    .dropzone {{
      padding: 14px;
      border: 1.5px dashed rgba(177,77,36,0.35);
      border-radius: 16px;
      background: rgba(177,77,36,0.05);
      color: var(--muted);
      text-align: center;
    }}
    .dropzone.active {{
      border-color: rgba(177,77,36,0.7);
      background: rgba(177,77,36,0.10);
      color: var(--accent);
    }}
    code {{ display: inline; padding: 2px 6px; border-radius: 8px; background: rgba(255,255,255,0.7); border: 1px solid var(--line); }}
    @media (max-width: 1080px) {{
      .columns {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">FaceFusion Role Reference Review</div>
      <h1>{title}</h1>
      <p class="sub">Review discovered face clusters before plan materialization. You can merge clusters into final roles, assign or override source faces, and directly edit the exported <code>decision_groups</code> JSON from this page.</p>
      <div class="stats">
        <div class="stat"><div class="label">Shots</div><div class="value" id="shotCount"></div></div>
        <div class="stat"><div class="label">Clusters</div><div class="value" id="clusterCount"></div></div>
        <div class="stat"><div class="label">Groups</div><div class="value" id="groupCount"></div></div>
        <div class="stat"><div class="label">Sources</div><div class="value" id="sourceCount"></div></div>
      </div>
      <div class="toolbar">
        <button class="button primary" id="addGroupButton" type="button">Add Group</button>
        <button class="button subtle" id="resetButton" type="button">Reset To Suggested</button>
        <button class="button subtle" id="applyJsonButton" type="button">Apply Raw JSON</button>
        <button class="button subtle" id="copyJsonButton" type="button">Copy JSON</button>
        <button class="button subtle" id="downloadJsonButton" type="button">Download JSON</button>
      </div>
      <div class="notice" id="statusBox">Use the group editor on the left, or edit the raw JSON on the right. Both stay in sync.</div>
    </section>
    <section class="columns">
      <div class="stack">
        <article class="card">
          <h2>Decision Groups</h2>
          <p class="sub">Each group becomes one final role. Merge by placing multiple clusters in the same group, then assign the source face for that role.</p>
          <div class="stack" id="groups"></div>
        </article>
        <article class="card">
          <h2>Detected Clusters</h2>
          <p class="sub">This section is read-only context for who the original footage seems to contain and where each cluster appears.</p>
          <section class="grid" id="clusters"></section>
        </article>
        <article class="card">
          <h2>Shot Pipeline Options</h2>
          <p class="sub">Default is off. Add optional per-shot pipeline operations such as lip sync, face enhancement, frame enhancement, background removal, expression restore, face edit, age modify, or colorization before you build the final plan.</p>
          <div class="toolbar">
            <button class="button subtle" id="selectAllFaceEnhanceButton" type="button">All Shots Face Repair</button>
            <button class="button subtle" id="selectAllLipSyncButton" type="button">All Shots Lip Sync</button>
            <button class="button subtle" id="clearAllShotOpsButton" type="button">Clear Shot Ops</button>
          </div>
          <div class="stack" id="shotOps"></div>
        </article>
      </div>
      <div class="stack">
        <article class="card">
          <h2>Raw Decisions JSON</h2>
          <p class="sub">This is the payload to pass into <code>facefusion_apply_reference_decisions(groups=[...])</code>.</p>
          <textarea class="raw-editor" id="rawEditor" spellcheck="false"></textarea>
        </article>
        <article class="card">
          <h2>Shot Operations JSON</h2>
          <p class="sub">This is the payload to pass into <code>facefusion_apply_shot_operation_decisions(shot_operations=[...])</code>.</p>
          <div class="toolbar">
            <button class="button subtle" id="applyShotOpsButton" type="button">Apply Shot Ops JSON</button>
          </div>
          <textarea class="raw-editor" id="shotOpsEditor" spellcheck="false"></textarea>
        </article>
        <article class="card">
          <h2>Validation</h2>
          <div class="facts" id="validationFacts"></div>
        </article>
        <article class="card">
          <h2>Defaults</h2>
          <p class="sub">Default extra operations, models, and face-selection settings are still applied here as prefills, but editing defaults from the UI is temporarily disabled. Change them through <code>facefusion.env.json</code>, the CLI/tool layer, or the agent.</p>
        </article>
        <article class="card">
          <h2>Source Candidates</h2>
          <div class="dropzone" id="sourceLibraryDropzone">Drop face image files here to add source candidates to the library.</div>
          <div class="catalog" id="sourceCatalog"></div>
        </article>
      </div>
    </section>
  </div>
  <script>
    const view = {payload};
    const clusters = view.clusters || [];
    const shots = view.shots || [];
    const sourceCandidates = view.source_candidates || [];
    const defaultMultiActorDefaults = view.multi_actor_defaults || {{ default_shot_operations: [], operation_defaults: {{}} }};
    const shotOperationCatalog = [
      {{ operation_type: "lip_sync", label: "Lip Sync", description: "Adds lip-sync operations. Multi-role shots expand into one speaking-role task per role.", role_mode: "per_role" }},
      {{ operation_type: "face_enhance", label: "Face Repair", description: "Adds a face enhancement cleanup pass for the shot.", role_mode: "global" }},
      {{ operation_type: "frame_enhance", label: "Frame Enhance", description: "Adds a whole-frame enhancement pass.", role_mode: "global" }},
      {{ operation_type: "background_remove", label: "Background Remove", description: "Adds a background removal pass.", role_mode: "global" }},
      {{ operation_type: "expression_restore", label: "Expression Restore", description: "Adds an expression restoration pass.", role_mode: "global" }},
      {{ operation_type: "face_edit", label: "Face Edit", description: "Adds a face editing pass for pose, gaze, or mouth adjustment.", role_mode: "global" }},
      {{ operation_type: "age_modify", label: "Age Modify", description: "Adds an age modification pass.", role_mode: "global" }},
      {{ operation_type: "frame_colorize", label: "Colorize", description: "Adds a colorization pass for grayscale or archival footage.", role_mode: "global" }},
    ];

    function slugify(value) {{
      return String(value || "")
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    }}

    function normalizeGroup(group, index) {{
      const prefill = group.prefill_source_candidate || group.source_candidate || null;
      return {{
        group_id: group.group_id || `group-${{String(index + 1).padStart(2, "0")}}`,
        cluster_ids: Array.from(new Set(group.cluster_ids || [])),
        role_name: group.role_name || group.suggested_role_name || `Role ${{index + 1}}`,
        role_id: group.role_id || group.suggested_role_id || slugify(group.role_name || group.suggested_role_name || `role-${{index + 1}}`),
        source_candidate_id: group.source_candidate_id || prefill?.candidate_id || "",
        source_path: group.source_path || prefill?.source_path || "",
        notes: group.notes || "",
      }};
    }}

    const fallbackGroups = (view.decision_groups || view.suggested_groups || []).map((group, index) => normalizeGroup(group, index));
    const state = {{
      groups: fallbackGroups.length ? fallbackGroups : clusters.map((cluster, index) => normalizeGroup({{
        group_id: `group-${{String(index + 1).padStart(2, "0")}}`,
        cluster_ids: [cluster.cluster_id],
        suggested_role_name: cluster.suggested_role_name || cluster.label || cluster.cluster_id,
        suggested_role_id: slugify(cluster.suggested_role_name || cluster.label || cluster.cluster_id),
        prefill_source_candidate: cluster.prefill_source_candidate || null,
      }}, index)),
      manualSourceCandidates: [],
      shotOperations: (shots || []).map((shot) => {{
        const enabled = new Set(defaultMultiActorDefaults.default_shot_operations || []);
        (shot.operations || []).forEach((operation) => {{
          if ((operation.operation_type || "") !== "face_swap") {{
            enabled.add(operation.operation_type);
          }}
        }});
        return {{
          shot_id: shot.shot_id,
          enabled_operations: Array.from(enabled),
          notes: "",
        }};
      }}),
    }};

    function allSourceCandidates() {{
      return [...sourceCandidates, ...state.manualSourceCandidates];
    }}

    function sourceByIdMap() {{
      return new Map(allSourceCandidates().map((candidate) => [candidate.candidate_id, candidate]));
    }}

    function clusterById(clusterId) {{
      return clusters.find((cluster) => cluster.cluster_id === clusterId) || null;
    }}

    function toExportGroups() {{
      return state.groups.map((group, index) => {{
        const payload = {{
          group_id: group.group_id || `group-${{String(index + 1).padStart(2, "0")}}`,
          cluster_ids: Array.from(new Set(group.cluster_ids || [])),
          role_name: group.role_name || `Role ${{index + 1}}`,
        }};
        if (group.role_id) payload.role_id = group.role_id;
        if (group.source_candidate_id) payload.source_candidate_id = group.source_candidate_id;
        if (group.source_path) payload.source_path = group.source_path;
        if (group.notes) payload.notes = group.notes;
        return payload;
      }});
    }}

    function setStatus(message, isError = false) {{
      const box = document.getElementById("statusBox");
      box.textContent = message;
      box.className = isError ? "notice error" : "notice";
    }}

    function sampleUrl(samplePath) {{
      if (!samplePath) return "";
      return samplePath.startsWith("file:") ? samplePath : "file:///" + samplePath.replace(/\\\\/g, "/");
    }}

    function clusterLabel(clusterId) {{
      const cluster = clusterById(clusterId);
      return cluster ? (cluster.suggested_role_name || cluster.label || cluster.cluster_id) : clusterId;
    }}

    function registerManualSourceFiles(files, targetGroupIndex = null) {{
      const accepted = Array.from(files || []).filter((file) => file && String(file.type || "").startsWith("image/"));
      if (!accepted.length) {{
        setStatus("No image files were detected in the drop payload.", true);
        return;
      }}
      const newCandidates = accepted.map((file, index) => {{
        const filePath = file.path || file.name || "";
        const baseName = (file.name || `manual-source-${{Date.now()}}-${{index + 1}}`).replace(/\\.[^.]+$/, "");
        return {{
          candidate_id: `manual-upload-${{Date.now()}}-${{index + 1}}`,
          label: baseName,
          source_path: filePath,
          preview_url: URL.createObjectURL(file),
          from_drop: true,
          path_uncertain: !file.path,
        }};
      }});
      state.manualSourceCandidates.push(...newCandidates);
      if (targetGroupIndex !== null && state.groups[targetGroupIndex]) {{
        const picked = newCandidates[0];
        state.groups[targetGroupIndex].source_candidate_id = picked.candidate_id;
        state.groups[targetGroupIndex].source_path = picked.source_path || "";
        if (!state.groups[targetGroupIndex].role_name || /^Role \\d+$/.test(state.groups[targetGroupIndex].role_name)) {{
          state.groups[targetGroupIndex].role_name = picked.label;
        }}
        if (!state.groups[targetGroupIndex].role_id || /^role-\\d+$/.test(state.groups[targetGroupIndex].role_id)) {{
          state.groups[targetGroupIndex].role_id = slugify(picked.label) || state.groups[targetGroupIndex].role_id;
        }}
      }}
      syncRawEditor();
      renderGroups();
      renderSourceCatalog();
      const uncertain = newCandidates.some((candidate) => candidate.path_uncertain);
      setStatus(
        uncertain
          ? "Added dropped image files. Browser did not expose a full local path for at least one file, so you may need to correct source_path in the JSON before apply."
          : "Added dropped image files as source candidates."
      );
    }}

    function moveClusterToGroup(clusterId, targetGroupIndex) {{
      state.groups.forEach((group, index) => {{
        const before = new Set(group.cluster_ids || []);
        if (index === targetGroupIndex) {{
          before.add(clusterId);
        }} else {{
          before.delete(clusterId);
        }}
        group.cluster_ids = Array.from(before);
      }});
      syncRawEditor();
      renderGroups();
    }}

    function enableDropzone(element, onDropCallback, activeClass = "active") {{
      ["dragenter", "dragover"].forEach((eventName) => {{
        element.addEventListener(eventName, (event) => {{
          event.preventDefault();
          element.classList.add(activeClass);
        }});
      }});
      ["dragleave", "dragend", "drop"].forEach((eventName) => {{
        element.addEventListener(eventName, () => {{
          element.classList.remove(activeClass);
        }});
      }});
      element.addEventListener("drop", (event) => {{
        event.preventDefault();
        onDropCallback(event);
      }});
    }}

    function renderStats() {{
      document.getElementById("shotCount").textContent = String((view.per_shot_summary || []).length);
      document.getElementById("clusterCount").textContent = String(clusters.length);
      document.getElementById("groupCount").textContent = String(state.groups.length);
      document.getElementById("sourceCount").textContent = String(allSourceCandidates().length);
    }}

    function validationSummary() {{
      const assigned = new Set();
      let duplicateAssignments = 0;
      let groupsMissingSource = 0;
      let groupsMissingClusters = 0;
      state.groups.forEach((group) => {{
        if (!(group.cluster_ids || []).length) groupsMissingClusters += 1;
        if (!group.source_candidate_id && !group.source_path) groupsMissingSource += 1;
        (group.cluster_ids || []).forEach((clusterId) => {{
          if (assigned.has(clusterId)) duplicateAssignments += 1;
          assigned.add(clusterId);
        }});
      }});
      const unassignedClusters = clusters.filter((cluster) => !assigned.has(cluster.cluster_id)).length;
      return {{ duplicateAssignments, groupsMissingSource, groupsMissingClusters, unassignedClusters }};
    }}

    function syncRawEditor() {{
      document.getElementById("rawEditor").value = JSON.stringify(toExportGroups(), null, 2);
      document.getElementById("shotOpsEditor").value = JSON.stringify(
        state.shotOperations.map((item) => {{
          const payload = {{
            shot_id: item.shot_id,
            enabled_operations: item.enabled_operations || [],
          }};
          if (item.notes) {{
            payload.notes = item.notes;
          }}
          return payload;
        }}),
        null,
        2
      );
      renderValidation();
      renderStats();
    }}

    function renderValidation() {{
      const summary = validationSummary();
      const root = document.getElementById("validationFacts");
      root.innerHTML = "";
      const enabledShotOps = state.shotOperations.reduce((count, item) => count + (item.enabled_operations || []).length, 0);
      [
        ["Groups", String(state.groups.length)],
        ["Duplicate Cluster Assignments", String(summary.duplicateAssignments)],
        ["Unassigned Clusters", String(summary.unassignedClusters)],
        ["Groups Missing Source", String(summary.groupsMissingSource)],
        ["Groups Missing Clusters", String(summary.groupsMissingClusters)],
        ["Shot Pipeline Ops", String(enabledShotOps)],
      ].forEach(([key, value]) => {{
        const fact = document.createElement("div");
        fact.className = "fact";
        const k = document.createElement("div");
        k.className = "k";
        k.textContent = key;
        const v = document.createElement("div");
        v.className = "v";
        v.textContent = value;
        fact.appendChild(k);
        fact.appendChild(v);
        root.appendChild(fact);
      }});
    }}

    function updateGroup(index, field, value) {{
      state.groups[index][field] = value;
      syncRawEditor();
      renderGroups();
    }}

    function toggleCluster(index, clusterId, checked) {{
      const clusterIds = new Set(state.groups[index].cluster_ids || []);
      if (checked) clusterIds.add(clusterId);
      else clusterIds.delete(clusterId);
      state.groups[index].cluster_ids = Array.from(clusterIds);
      syncRawEditor();
      renderGroups();
    }}

    function updateShotOperation(shotId, operationType, checked) {{
      const shotState = state.shotOperations.find((item) => item.shot_id === shotId);
      if (!shotState) {{
        return;
      }}
      const enabled = new Set(shotState.enabled_operations || []);
      if (checked) {{
        enabled.add(operationType);
      }} else {{
        enabled.delete(operationType);
      }}
      shotState.enabled_operations = Array.from(enabled);
      syncRawEditor();
      renderShotOperations();
    }}

    function setShotOperationForAll(operationType, checked) {{
      state.shotOperations.forEach((shotState) => {{
        const enabled = new Set(shotState.enabled_operations || []);
        if (checked) {{
          enabled.add(operationType);
        }} else {{
          enabled.delete(operationType);
        }}
        shotState.enabled_operations = Array.from(enabled);
      }});
      syncRawEditor();
      renderShotOperations();
    }}

    function renderShotOperations() {{
      const root = document.getElementById("shotOps");
      root.innerHTML = "";
      shots.forEach((shot) => {{
        const shotState = state.shotOperations.find((item) => item.shot_id === shot.shot_id) || {{
          shot_id: shot.shot_id,
          enabled_operations: [],
          notes: "",
        }};
        const card = document.createElement("section");
        card.className = "shot-op-card";
        const title = document.createElement("h3");
        title.textContent = shot.shot_id;
        card.appendChild(title);
        const meta = document.createElement("div");
        meta.className = "muted";
        meta.textContent = [shot.target_path, shot.trim_start ?? shot.frame_start, shot.trim_end ?? shot.frame_end].filter((value) => value !== null && value !== undefined && value !== "").join(" | ");
        card.appendChild(meta);
        const roles = document.createElement("div");
        roles.className = "badge-row";
        (shot.roles || []).forEach((roleId) => {{
          const chip = document.createElement("span");
          chip.className = "chip";
          chip.textContent = roleId;
          roles.appendChild(chip);
        }});
        if (!(shot.roles || []).length) {{
          const chip = document.createElement("span");
          chip.className = "chip warn";
          chip.textContent = "No roles assigned yet";
          roles.appendChild(chip);
        }}
        card.appendChild(roles);
        const opGrid = document.createElement("div");
        opGrid.className = "op-grid";
        shotOperationCatalog.forEach((op) => {{
          const wrap = document.createElement("label");
          wrap.className = "op-toggle";
          const box = document.createElement("input");
          box.type = "checkbox";
          box.checked = (shotState.enabled_operations || []).includes(op.operation_type);
          box.addEventListener("change", (event) => updateShotOperation(shot.shot_id, op.operation_type, event.target.checked));
          wrap.appendChild(box);
          const textWrap = document.createElement("div");
          const name = document.createElement("strong");
          name.textContent = op.label;
          textWrap.appendChild(name);
          const desc = document.createElement("div");
          desc.className = "muted";
          desc.textContent = op.description;
          textWrap.appendChild(desc);
          if (op.operation_type === "lip_sync" && (shot.roles || []).length > 1) {{
            const note = document.createElement("div");
            note.className = "muted";
            note.textContent = "This shot has multiple roles. Lip sync will expand to one operation per role.";
            textWrap.appendChild(note);
          }}
          wrap.appendChild(textWrap);
          opGrid.appendChild(wrap);
        }});
        card.appendChild(opGrid);
        root.appendChild(card);
      }});
    }}

    function renderGroups() {{
      const summary = validationSummary();
      const root = document.getElementById("groups");
      root.innerHTML = "";
      state.groups.forEach((group, index) => {{
        const card = document.createElement("section");
        card.className = "group-card";
        enableDropzone(card, (event) => {{
          const clusterId = event.dataTransfer.getData("text/cluster-id");
          if (clusterId) {{
            moveClusterToGroup(clusterId, index);
            setStatus(`Moved ${{clusterLabel(clusterId)}} into ${{group.role_name || group.group_id}}.`);
            return;
          }}
          if (event.dataTransfer.files && event.dataTransfer.files.length) {{
            registerManualSourceFiles(event.dataTransfer.files, index);
          }}
        }}, "drop-target");
        const header = document.createElement("div");
        header.className = "group-header";
        const titleWrap = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = group.role_name || group.group_id || `Group ${{index + 1}}`;
        titleWrap.appendChild(title);
        const subtitle = document.createElement("div");
        subtitle.className = "muted";
        subtitle.textContent = group.group_id || `group-${{String(index + 1).padStart(2, "0")}}`;
        titleWrap.appendChild(subtitle);
        header.appendChild(titleWrap);
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button danger";
        remove.textContent = "Remove";
        remove.addEventListener("click", () => {{
          state.groups.splice(index, 1);
          syncRawEditor();
          renderGroups();
        }});
        header.appendChild(remove);
        card.appendChild(header);

        const fields = document.createElement("div");
        fields.className = "editor-grid";
        [
          ["Group ID", "group_id"],
          ["Role Name", "role_name"],
          ["Role ID", "role_id"],
        ].forEach(([labelText, key]) => {{
          const field = document.createElement("div");
          field.className = "field";
          const label = document.createElement("label");
          label.textContent = labelText;
          const input = document.createElement("input");
          input.type = "text";
          input.value = group[key] || "";
          input.addEventListener("input", (event) => updateGroup(index, key, event.target.value));
          field.appendChild(label);
          field.appendChild(input);
          fields.appendChild(field);
        }});

        const sourceField = document.createElement("div");
        sourceField.className = "field";
        const sourceLabel = document.createElement("label");
        sourceLabel.textContent = "Source Candidate";
        const sourceSelect = document.createElement("select");
        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "No source selected";
        sourceSelect.appendChild(emptyOption);
        allSourceCandidates().forEach((candidate) => {{
          const option = document.createElement("option");
          option.value = candidate.candidate_id;
          option.textContent = `${{candidate.label}}${{candidate.source_path ? " -> " + candidate.source_path : ""}}`;
          if (candidate.candidate_id === group.source_candidate_id) option.selected = true;
          sourceSelect.appendChild(option);
        }});
        sourceSelect.addEventListener("change", (event) => {{
          const candidateId = event.target.value;
          const candidate = sourceByIdMap().get(candidateId);
          state.groups[index].source_candidate_id = candidateId;
          if (candidate && !state.groups[index].source_path) {{
            state.groups[index].source_path = candidate.source_path || "";
          }}
          syncRawEditor();
          renderGroups();
        }});
        sourceField.appendChild(sourceLabel);
        sourceField.appendChild(sourceSelect);
        fields.appendChild(sourceField);
        card.appendChild(fields);

        const pathField = document.createElement("div");
        pathField.className = "field";
        const pathLabel = document.createElement("label");
        pathLabel.textContent = "Source Path Override";
        const pathInput = document.createElement("input");
        pathInput.type = "text";
        pathInput.value = group.source_path || "";
        pathInput.addEventListener("input", (event) => updateGroup(index, "source_path", event.target.value));
        pathField.appendChild(pathLabel);
        pathField.appendChild(pathInput);
        card.appendChild(pathField);

        const notesField = document.createElement("div");
        notesField.className = "field";
        const notesLabel = document.createElement("label");
        notesLabel.textContent = "Notes";
        const notesInput = document.createElement("textarea");
        notesInput.value = group.notes || "";
        notesInput.addEventListener("input", (event) => updateGroup(index, "notes", event.target.value));
        notesField.appendChild(notesLabel);
        notesField.appendChild(notesInput);
        card.appendChild(notesField);

        const assignLabel = document.createElement("label");
        assignLabel.className = "muted";
        assignLabel.textContent = "Merged Cluster Set";
        card.appendChild(assignLabel);
        const bucket = document.createElement("div");
        bucket.className = "cluster-bucket";
        (group.cluster_ids || []).forEach((clusterId) => {{
          const token = document.createElement("div");
          token.className = "cluster-token";
          token.draggable = true;
          token.addEventListener("dragstart", (event) => {{
            event.dataTransfer.setData("text/cluster-id", clusterId);
          }});
          const avatar = document.createElement("img");
          const cluster = clusterById(clusterId);
          avatar.src = sampleUrl(cluster && (cluster.sample_paths || [])[0]);
          avatar.alt = clusterId;
          token.appendChild(avatar);
          const text = document.createElement("span");
          text.textContent = clusterLabel(clusterId);
          token.appendChild(text);
          bucket.appendChild(token);
        }});
        if (!(group.cluster_ids || []).length) {{
          const empty = document.createElement("div");
          empty.className = "muted";
          empty.textContent = "Drag detected clusters here to merge them into this role.";
          bucket.appendChild(empty);
        }}
        card.appendChild(bucket);

        const clusterFieldLabel = document.createElement("label");
        clusterFieldLabel.className = "muted";
        clusterFieldLabel.textContent = "Included Clusters (checkbox or drag)";
        card.appendChild(clusterFieldLabel);
        const picker = document.createElement("div");
        picker.className = "cluster-picker";
        clusters.forEach((cluster) => {{
          const active = (group.cluster_ids || []).includes(cluster.cluster_id);
          const option = document.createElement("label");
          option.className = "cluster-option" + (active ? " active" : "");
          option.draggable = true;
          option.addEventListener("dragstart", (event) => {{
            option.classList.add("dragging");
            event.dataTransfer.setData("text/cluster-id", cluster.cluster_id);
          }});
          option.addEventListener("dragend", () => {{
            option.classList.remove("dragging");
          }});
          const top = document.createElement("div");
          top.style.display = "flex";
          top.style.justifyContent = "space-between";
          top.style.alignItems = "center";
          const check = document.createElement("input");
          check.type = "checkbox";
          check.checked = active;
          check.addEventListener("change", (event) => toggleCluster(index, cluster.cluster_id, event.target.checked));
          const name = document.createElement("strong");
          name.textContent = cluster.suggested_role_name || cluster.label || cluster.cluster_id;
          top.appendChild(check);
          top.appendChild(name);
          option.appendChild(top);
          const img = document.createElement("img");
          img.className = "cluster-thumb";
          img.src = sampleUrl((cluster.sample_paths || [])[0]);
          img.alt = cluster.cluster_id;
          option.appendChild(img);
          const meta = document.createElement("div");
          meta.className = "muted";
          meta.textContent = `${{cluster.cluster_id}} | shots: ${{(cluster.shot_ids || []).join(", ") || "n/a"}}`;
          option.appendChild(meta);
          picker.appendChild(option);
        }});
        card.appendChild(picker);

        const badges = document.createElement("div");
        badges.className = "badge-row";
        if (!(group.cluster_ids || []).length) {{
          const chip = document.createElement("span");
          chip.className = "chip warn";
          chip.textContent = "No clusters assigned";
          badges.appendChild(chip);
        }}
        if (!group.source_candidate_id && !group.source_path) {{
          const chip = document.createElement("span");
          chip.className = "chip warn";
          chip.textContent = "Missing source";
          badges.appendChild(chip);
        }} else {{
          const chip = document.createElement("span");
          chip.className = "chip ok";
          chip.textContent = group.source_candidate_id ? `Source: ${{group.source_candidate_id}}` : "Manual source path";
          badges.appendChild(chip);
        }}
        if (summary.duplicateAssignments > 0) {{
          const dupes = new Set();
          state.groups.forEach((otherGroup, otherIndex) => {{
            if (otherIndex === index) return;
            (otherGroup.cluster_ids || []).forEach((clusterId) => {{
              if ((group.cluster_ids || []).includes(clusterId)) dupes.add(clusterId);
            }});
          }});
          if (dupes.size) {{
            const chip = document.createElement("span");
            chip.className = "chip warn";
            chip.textContent = `Duplicate: ${{Array.from(dupes).join(", ")}}`;
            badges.appendChild(chip);
          }}
        }}
        card.appendChild(badges);
        root.appendChild(card);
      }});
    }}

    function renderClusterCatalog() {{
      const root = document.getElementById("clusters");
      root.innerHTML = "";
      clusters.forEach((cluster) => {{
        const card = document.createElement("article");
        card.className = "card";
        const heading = document.createElement("h3");
        heading.textContent = cluster.suggested_role_name || cluster.label || cluster.cluster_id;
        card.appendChild(heading);
        const meta = document.createElement("p");
        meta.className = "muted";
        meta.textContent = `${{cluster.cluster_id}} | shots: ${{(cluster.shot_ids || []).join(", ") || "n/a"}} | samples: ${{cluster.sample_count || 0}}`;
        card.appendChild(meta);
        if (cluster.prefill_source_candidate) {{
          const hint = document.createElement("p");
          hint.className = "muted";
          hint.textContent = `Prefill source: ${{cluster.prefill_source_candidate.label}}${{cluster.prefill_source_candidate.source_path ? " -> " + cluster.prefill_source_candidate.source_path : ""}}`;
          card.appendChild(hint);
        }}
        const chipRow = document.createElement("div");
        (cluster.shot_ids || []).forEach((shotId) => {{
          const chip = document.createElement("span");
          chip.className = "chip";
          chip.textContent = shotId;
          chipRow.appendChild(chip);
        }});
        card.appendChild(chipRow);
        const sampleGrid = document.createElement("div");
        sampleGrid.className = "samples";
        (cluster.sample_paths || []).slice(0, 6).forEach((samplePath) => {{
          const img = document.createElement("img");
          img.src = sampleUrl(samplePath);
          img.alt = cluster.cluster_id;
          sampleGrid.appendChild(img);
        }});
        card.appendChild(sampleGrid);
        root.appendChild(card);
      }});
    }}

    function renderSourceCatalog() {{
      const root = document.getElementById("sourceCatalog");
      root.innerHTML = "";
      const candidates = allSourceCandidates();
      if (!candidates.length) {{
        const empty = document.createElement("div");
        empty.className = "muted";
        empty.textContent = "No source candidates found in references.json.";
        root.appendChild(empty);
        return;
      }}
      candidates.forEach((candidate) => {{
        const item = document.createElement("div");
        item.className = "catalog-item";
        if (candidate.preview_url) {{
          const img = document.createElement("img");
          img.src = candidate.preview_url;
          img.alt = candidate.label || candidate.candidate_id;
          item.appendChild(img);
        }}
        const heading = document.createElement("strong");
        heading.textContent = candidate.label || candidate.candidate_id;
        item.appendChild(heading);
        const id = document.createElement("div");
        id.className = "muted";
        id.textContent = candidate.candidate_id;
        item.appendChild(id);
        if (candidate.source_path) {{
          const path = document.createElement("div");
          path.className = "muted";
          path.textContent = candidate.source_path;
          item.appendChild(path);
        }}
        root.appendChild(item);
      }});
    }}

    function addGroup() {{
      state.groups.push(normalizeGroup({{
        group_id: `group-${{String(state.groups.length + 1).padStart(2, "0")}}`,
        cluster_ids: [],
        role_name: `Role ${{state.groups.length + 1}}`,
        role_id: `role-${{String(state.groups.length + 1).padStart(2, "0")}}`,
      }}, state.groups.length));
      syncRawEditor();
      renderGroups();
      setStatus("Added a new empty decision group.");
    }}

    function applyRawEditor() {{
      const raw = document.getElementById("rawEditor").value.trim();
      try {{
        const parsed = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(parsed)) throw new Error("Raw JSON must be an array of groups.");
        state.groups = parsed.map((group, index) => normalizeGroup(group, index));
        syncRawEditor();
        renderGroups();
        setStatus("Applied raw JSON into the visual editor.");
      }} catch (error) {{
        setStatus(error.message || String(error), true);
      }}
    }}

    async function copyJson() {{
      const text = document.getElementById("rawEditor").value;
      try {{
        await navigator.clipboard.writeText(text);
        setStatus("Copied decision_groups JSON to clipboard.");
      }} catch (error) {{
        setStatus("Clipboard copy failed. You can still copy from the raw editor manually.", true);
      }}
    }}

    function downloadJson() {{
      const blob = new Blob([document.getElementById("rawEditor").value], {{ type: "application/json" }});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${{view.project_id || "facefusion-project"}}-decision-groups.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      setStatus("Downloaded the decision_groups JSON file.");
    }}

    function applyShotOpsEditor() {{
      const raw = document.getElementById("shotOpsEditor").value.trim();
      try {{
        const parsed = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(parsed)) throw new Error("Shot operations JSON must be an array.");
        state.shotOperations = parsed.map((item) => {{
          const enabled = Array.isArray(item.enabled_operations) ? item.enabled_operations.filter(Boolean) : [];
          return {{
            shot_id: item.shot_id,
            enabled_operations: Array.from(new Set(enabled)),
            notes: item.notes || "",
          }};
        }});
        syncRawEditor();
        renderShotOperations();
        setStatus("Applied shot operations JSON into the visual editor.");
      }} catch (error) {{
        setStatus(error.message || String(error), true);
      }}
    }}

    document.getElementById("addGroupButton").addEventListener("click", addGroup);
    document.getElementById("resetButton").addEventListener("click", () => {{
      state.groups = fallbackGroups.length ? fallbackGroups.map((group, index) => normalizeGroup(group, index)) : [];
      state.manualSourceCandidates = [];
      syncRawEditor();
      renderGroups();
      renderShotOperations();
      renderSourceCatalog();
      setStatus("Reset editor state back to the suggested groups.");
    }});
    document.getElementById("applyJsonButton").addEventListener("click", applyRawEditor);
    document.getElementById("applyShotOpsButton").addEventListener("click", applyShotOpsEditor);
    document.getElementById("copyJsonButton").addEventListener("click", copyJson);
    document.getElementById("downloadJsonButton").addEventListener("click", downloadJson);
    document.getElementById("selectAllFaceEnhanceButton").addEventListener("click", () => {{
      setShotOperationForAll("face_enhance", true);
      setStatus("Enabled face repair for all shots.");
    }});
    document.getElementById("selectAllLipSyncButton").addEventListener("click", () => {{
      setShotOperationForAll("lip_sync", true);
      setStatus("Enabled lip sync for all shots.");
    }});
    document.getElementById("clearAllShotOpsButton").addEventListener("click", () => {{
      state.shotOperations.forEach((shotState) => {{
        shotState.enabled_operations = [];
      }});
      syncRawEditor();
      renderShotOperations();
      setStatus("Cleared all optional shot pipeline operations.");
    }});
    enableDropzone(document.getElementById("sourceLibraryDropzone"), (event) => {{
      if (event.dataTransfer.files && event.dataTransfer.files.length) {{
        registerManualSourceFiles(event.dataTransfer.files, null);
      }}
    }});

    renderStats();
    renderClusterCatalog();
    renderShotOperations();
    renderSourceCatalog();
    syncRawEditor();
    renderGroups();
  </script>
</body>
</html>
"""


@mcp.tool(description="Check whether the local FaceFusion installation can run on this machine.", structured_output=True)
def facefusion_health_check(
    facefusion_root: str | None = None,
    python_path: str | None = None,
    include_models: bool = True,
) -> dict[str, Any]:
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    env_config = _read_env_config()
    git_check = _command_available("git", cwd=PLUGIN_ROOT)
    ffmpeg_check = _run_subprocess(["ffmpeg", "-version"], cwd=root if root.exists() else PLUGIN_ROOT)
    version_check = _run_facefusion_command(["-v"], facefusion_root=facefusion_root, python_path=python_path)
    providers = _available_providers(facefusion_root=facefusion_root, python_path=python_path)
    models = _models_summary(facefusion_root=facefusion_root) if include_models else None
    entrypoint_exists = (root / "facefusion.py").exists()
    python_exists = python_exe.exists()
    needs_install = not entrypoint_exists
    needs_setup = entrypoint_exists and not python_exists
    ready = all(
        [
            root.exists(),
            python_exists,
            entrypoint_exists,
            ffmpeg_check["success"],
            version_check["success"],
        ]
    )
    missing_components = []
    if not root.exists():
        missing_components.append("facefusion_root")
    if not entrypoint_exists:
        missing_components.append("facefusion_checkout")
    if not python_exists:
        missing_components.append("facefusion_venv")
    if not ffmpeg_check["success"]:
        missing_components.append("ffmpeg")
    install_recommendation = "ready"
    if needs_install or needs_setup:
        install_recommendation = "install_or_setup_facefusion"
    elif not ffmpeg_check["success"]:
        install_recommendation = "install_ffmpeg_manually"
    return {
        "facefusion_root": str(root),
        "python_path": str(python_exe),
        "env_config_path": str(ENV_CONFIG_PATH),
        "env_config": env_config,
        "default_ui_mode": _default_ui_mode(),
        "facefusion_version": version_check["stdout"].strip(),
        "git_available": git_check["success"],
        "ffmpeg_available": ffmpeg_check["success"],
        "ffmpeg_summary": ffmpeg_check["stdout_summary"],
        "execution_providers": providers,
        "paths": {
            "facefusion_root_exists": root.exists(),
            "python_exists": python_exists,
            "entrypoint_exists": entrypoint_exists,
            "models_dir_exists": (root / ".assets" / "models").exists(),
        },
        "models": models,
        "can_run": ready,
        "needs_install": needs_install,
        "needs_setup": needs_setup,
        "missing_components": missing_components,
        "suggested_install_root": str(_recommended_install_root(facefusion_root)),
        "can_auto_install_or_setup": git_check["success"],
        "install_recommendation": install_recommendation,
        "checks": {
            "version_command": version_check,
            "ffmpeg_command": ffmpeg_check,
            "git_command": git_check,
        },
    }


@mcp.tool(description="List the current machine's FaceFusion commands, processors, providers, and encoders.", structured_output=True)
def facefusion_list_capabilities(
    category: str = "all",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    choice_catalog = _available_choice_catalog(facefusion_root=facefusion_root, python_path=python_path)
    capabilities = {
        "commands": DEFAULT_COMMANDS,
        "processors": _available_processors(facefusion_root=facefusion_root),
        "providers": _available_providers(facefusion_root=facefusion_root, python_path=python_path),
        "encoders": _available_encoders(facefusion_root=facefusion_root, python_path=python_path),
        "ui_layouts": choice_catalog.get("ui_layouts", []),
        "ui_workflows": choice_catalog.get("ui_workflows", []),
        "download": {
            "providers": choice_catalog.get("download_providers", []),
            "scopes": choice_catalog.get("download_scopes", []),
        },
        "memory": {
            "video_memory_strategies": choice_catalog.get("video_memory_strategies", []),
            "execution_thread_count_range": choice_catalog.get("execution_thread_count_range", []),
            "system_memory_limit_range": choice_catalog.get("system_memory_limit_range", []),
        },
        "benchmark": {
            "modes": choice_catalog.get("benchmark_modes", []),
            "resolutions": choice_catalog.get("benchmark_resolutions", []),
            "cycle_count_range": choice_catalog.get("benchmark_cycle_count_range", []),
        },
        "face": choice_catalog.get("face", {}),
        "output": choice_catalog.get("output", {}),
        "processor_models": choice_catalog.get("processor_models", {}),
        "presets": PRESET_LIBRARY,
    }
    if category == "all":
        return capabilities
    if category not in capabilities:
        raise ValueError(f"Unknown category: {category}")
    return {category: capabilities[category]}


@mcp.tool(description="List the built-in FaceFusion MCP presets and their merged defaults.", structured_output=True)
def facefusion_list_presets() -> dict[str, Any]:
    return {
        "preset_count": len(PRESET_LIBRARY),
        "presets": PRESET_LIBRARY,
    }


@mcp.tool(description="Update persistent plugin defaults in facefusion.env.json, including multi-actor default extra operations and default model or face-selection settings.", structured_output=True)
def facefusion_update_multi_actor_defaults(
    default_shot_operations: list[str] | None = None,
    operation_defaults: dict[str, Any] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    env_config = _read_env_config()
    current = _default_multi_actor_defaults()
    next_defaults: dict[str, Any] = {}
    if default_shot_operations is not None:
        next_defaults["default_shot_operations"] = list(default_shot_operations)
    if operation_defaults is not None:
        next_defaults["operation_defaults"] = dict(operation_defaults)
    merged = next_defaults if replace else _merge_deep_dict(current, next_defaults)
    env_config["multi_actor_defaults"] = merged
    _write_env_config(env_config)
    return {
        "success": True,
        "env_config_path": str(ENV_CONFIG_PATH),
        "multi_actor_defaults": merged,
    }


@mcp.tool(description="Check the FaceFusion queue worker and summarize queued, failed, completed, and drafted jobs.", structured_output=True)
def facefusion_check_queue(
    jobs_path: str | None = None,
    log_level: str = "info",
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    runner_state = _read_runner_state()
    active_runner_state = _get_active_runner_state()
    statuses = ["drafted", "queued", "failed", "completed"]
    results: dict[str, Any] = {}
    counts: dict[str, int] = {}
    overall_success = True
    for status in statuses:
        result = _list_jobs_by_status(
            status,
            jobs_path=jobs_path,
            log_level=log_level,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
        results[status] = result
        counts[status] = _count_job_rows((result.get("stdout") or "") + (result.get("stderr") or ""))
        overall_success = overall_success and result.get("success", False)
    return {
        "success": overall_success,
        "runner": {
            "state_path": str(RUNNER_STATE_PATH),
            "active": bool(active_runner_state),
            "state": active_runner_state or runner_state,
        },
        "counts": counts,
        "jobs_path": jobs_path or ".jobs",
        "results": results,
    }


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


@mcp.tool(description="Install or set up a local FaceFusion checkout after explicit confirmation.", structured_output=True)
def facefusion_install_or_setup(
    confirmed: bool,
    install_root: str | None = None,
    repo_url: str = FACEFUSION_REPO_URL,
    ref: str | None = None,
    onnxruntime_variant: str = "cuda",
    force_reinstall: bool = False,
    preload_models: bool = False,
    model_scope: str = "lite",
) -> dict[str, Any]:
    target_root = _recommended_install_root(install_root)
    venv_info = _venv_paths(target_root)
    plan = {
        "install_root": str(target_root),
        "repo_url": repo_url,
        "ref": ref,
        "onnxruntime_variant": onnxruntime_variant,
        "force_reinstall": force_reinstall,
        "preload_models": preload_models,
        "model_scope": model_scope,
        "steps": [
            "clone_or_reuse_checkout",
            "create_or_reuse_venv",
            "upgrade_pip",
            "run_facefusion_installer",
            "optional_model_preload",
        ],
    }
    if not confirmed:
        return {
            "confirmed": False,
            "performed": False,
            "message": "Confirmation required before installation or setup changes are made.",
            "plan": plan,
        }

    git_check = _command_available("git", cwd=PLUGIN_ROOT)
    if not git_check["success"]:
        return {
            "confirmed": True,
            "performed": False,
            "message": "git is required to clone or update FaceFusion.",
            "plan": plan,
            "git_check": git_check,
        }

    commands_run: list[dict[str, Any]] = []
    _ensure_directory(target_root.parent)
    checkout_exists = (target_root / "facefusion.py").exists()
    if not checkout_exists:
        clone_args = ["git", "clone", repo_url, str(target_root)]
        if ref:
            clone_args = ["git", "clone", "--branch", ref, repo_url, str(target_root)]
        clone_result = _run_subprocess(clone_args, cwd=target_root.parent)
        commands_run.append({"step": "clone_checkout", "result": clone_result})
        if not clone_result["success"]:
            return {
                "confirmed": True,
                "performed": False,
                "plan": plan,
                "commands_run": commands_run,
                "health_check": facefusion_health_check(facefusion_root=str(target_root), include_models=False),
            }
    elif ref:
        checkout_ref_result = _run_subprocess(["git", "checkout", ref], cwd=target_root)
        commands_run.append({"step": "checkout_ref", "result": checkout_ref_result})
        if not checkout_ref_result["success"]:
            return {
                "confirmed": True,
                "performed": False,
                "plan": plan,
                "commands_run": commands_run,
                "health_check": facefusion_health_check(facefusion_root=str(target_root), include_models=False),
            }

    if not venv_info["python"].exists():
        _ensure_directory(target_root)
        venv.create(str(venv_info["venv_root"]), with_pip=True)
        commands_run.append(
            {
                "step": "create_venv",
                "result": {
                    "command": [sys.executable, "-m", "venv", str(venv_info["venv_root"])],
                    "cwd": str(target_root),
                    "return_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "stdout_summary": "",
                    "stderr_summary": "",
                    "success": True,
                },
            }
        )

    venv_env = _venv_env(target_root)
    pip_upgrade = _run_subprocess([str(venv_info["python"]), "-m", "pip", "install", "--upgrade", "pip"], cwd=target_root, env=venv_env)
    commands_run.append({"step": "upgrade_pip", "result": pip_upgrade})
    if not pip_upgrade["success"]:
        return {
            "confirmed": True,
            "performed": False,
            "plan": plan,
            "commands_run": commands_run,
            "health_check": facefusion_health_check(facefusion_root=str(target_root), python_path=str(venv_info["python"]), include_models=False),
        }

    install_args = [str(venv_info["python"]), "install.py", "--onnxruntime", onnxruntime_variant, "--skip-conda"]
    if force_reinstall:
        install_args.append("--force-reinstall")
    install_result = _run_subprocess(install_args, cwd=target_root, env=venv_env)
    commands_run.append({"step": "install_dependencies", "result": install_result})
    if not install_result["success"]:
        return {
            "confirmed": True,
            "performed": False,
            "plan": plan,
            "commands_run": commands_run,
            "health_check": facefusion_health_check(facefusion_root=str(target_root), python_path=str(venv_info["python"]), include_models=False),
        }

    if preload_models:
        preload_result = _run_subprocess(
            [str(venv_info["python"]), "facefusion.py", "force-download", "--download-scope", model_scope, "--log-level", "info"],
            cwd=target_root,
            env=venv_env,
        )
        commands_run.append({"step": "preload_models", "result": preload_result})

    post_health = facefusion_health_check(facefusion_root=str(target_root), python_path=str(venv_info["python"]))
    updated_env_config = _read_env_config()
    updated_env_config.update(
        {
            "facefusion_root": str(target_root),
            "python_path": str(venv_info["python"]),
            "managed_by_plugin": True,
            "repo_url": repo_url,
            "ref": ref,
        }
    )
    _write_env_config(updated_env_config)
    post_health = facefusion_health_check(facefusion_root=str(target_root), python_path=str(venv_info["python"]))
    return {
        "confirmed": True,
        "performed": True,
        "plan": plan,
        "commands_run": commands_run,
        "facefusion_root": str(target_root),
        "python_path": str(venv_info["python"]),
        "health_check": post_health,
    }


@mcp.tool(description="Run a single local FaceFusion processing task without the UI.", structured_output=True)
def facefusion_run_job(
    source_paths: list[str],
    target_path: str,
    output_path: str,
    preset: str | None = None,
    enqueue: bool | None = None,
    jobs_path: str | None = None,
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
    resolved, effective_preset = _resolve_runtime_bundle(
        preset,
        defaults_bucket="tool_defaults",
        defaults_name="run_job",
        fallback_processors=None,
        processors=processors,
        execution=execution,
        output_options=output_options,
        memory_options=memory_options,
        face_options=face_options,
        download_options=download_options,
        misc_options=misc_options,
        extra_args=extra_args,
    )
    queue_mode = _default_enqueue_tasks() if enqueue is None else enqueue
    normalized_misc_options, skip_nsfw_check = _extract_skip_nsfw_check(resolved["misc_options"])
    for source_path in source_paths:
        _require_existing_file(source_path, "source_paths item")
    _require_existing_file(target_path, "target_path")
    _ensure_output_allowed(output_path, resolved["output_options"])

    args = ["headless-run", "-s", *source_paths, "-t", target_path, "-o", output_path]
    args.extend(
        _build_common_run_args(
            processors=resolved["processors"],
            execution=resolved["execution"],
            output_options=resolved["output_options"],
            memory_options=resolved["memory_options"],
            face_options=resolved["face_options"],
            download_options=resolved["download_options"],
            misc_options=normalized_misc_options,
            extra_args=resolved["extra_args"],
            facefusion_root=facefusion_root,
            python_path=python_path,
            include_default_execution=True,
        )
    )
    normalized = {
        "source_paths": source_paths,
        "target_path": target_path,
        "output_path": output_path,
        "preset": effective_preset,
        "enqueue": queue_mode,
        "jobs_path": jobs_path,
        "processors": resolved["processors"],
        "execution": resolved["execution"] or {"providers": _default_provider(facefusion_root=facefusion_root, python_path=python_path)},
        "output_options": resolved["output_options"],
        "memory_options": resolved["memory_options"],
        "face_options": resolved["face_options"],
        "download_options": resolved["download_options"],
        "misc_options": normalized_misc_options or {"log_level": "info"},
        "extra_args": resolved["extra_args"],
        "skip_nsfw_check": skip_nsfw_check,
    }
    if queue_mode:
        step_request = {
            "source_paths": source_paths,
            "target_path": target_path,
            "output_path": output_path,
            "processors": resolved["processors"],
            "output_options": resolved["output_options"],
            "face_options": resolved["face_options"],
            "extra_args": list(resolved["extra_args"]),
        }
        queue_result = _queue_single_step_job(
            job_prefix="run",
            target_path=target_path,
            step_request=step_request,
            jobs_path=jobs_path,
            log_level=normalized_misc_options.get("log_level", "info"),
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
        return {
            **queue_result,
            "mode": "queued",
            "queue_runtime_note": "Execution, memory, and download runtime options are applied when queued jobs are run, not when the step is drafted.",
            "normalized_request": normalized,
            "output_path": output_path,
            "output_exists": Path(output_path).exists(),
            "skip_nsfw_check": skip_nsfw_check,
        }
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path, skip_nsfw_check=skip_nsfw_check)
    return {
        **result,
        "mode": "executed",
        "normalized_request": normalized,
        "output_path": output_path,
        "output_exists": Path(output_path).exists(),
        "skip_nsfw_check": skip_nsfw_check,
    }


@mcp.tool(description="Launch the local FaceFusion interactive UI, or preview the launch command in dry-run mode.", structured_output=True)
def facefusion_launch_ui(
    source_paths: list[str] | None = None,
    target_path: str | None = None,
    output_path: str | None = None,
    preset: str | None = None,
    processors: list[str] | None = None,
    execution: dict[str, Any] | None = None,
    memory_options: dict[str, Any] | None = None,
    face_options: dict[str, Any] | None = None,
    download_options: dict[str, Any] | None = None,
    misc_options: dict[str, Any] | None = None,
    open_browser: bool = True,
    ui_layouts: list[str] | None = None,
    ui_workflow: str | None = None,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    resolved, effective_preset = _resolve_runtime_bundle(
        preset,
        defaults_bucket="tool_defaults",
        defaults_name="launch_ui",
        fallback_processors=None,
        processors=processors,
        execution=execution,
        output_options=None,
        memory_options=memory_options,
        face_options=face_options,
        download_options=download_options,
        misc_options=misc_options,
        extra_args=extra_args,
    )
    normalized_misc_options, skip_nsfw_check = _extract_skip_nsfw_check(resolved["misc_options"])
    normalized_sources = list(source_paths or [])
    for source_path in normalized_sources:
        _require_existing_file(source_path, "source_paths item")
    if target_path:
        _require_existing_file(target_path, "target_path")

    args = ["run"]
    if normalized_sources:
        args.extend(["-s", *normalized_sources])
    if target_path:
        args.extend(["-t", target_path])
    if output_path:
        args.extend(["-o", output_path])
    if open_browser:
        args.append("--open-browser")
    if ui_layouts:
        args.extend(["--ui-layouts", *ui_layouts])
    if ui_workflow:
        args.extend(["--ui-workflow", ui_workflow])
    args.extend(
        _build_common_run_args(
            processors=resolved["processors"],
            execution=resolved["execution"],
            output_options=None,
            memory_options=resolved["memory_options"],
            face_options=resolved["face_options"],
            download_options=resolved["download_options"],
            misc_options=normalized_misc_options,
            extra_args=resolved["extra_args"],
            facefusion_root=facefusion_root,
            python_path=python_path,
            include_default_execution=True,
        )
    )
    root = _facefusion_root(facefusion_root)
    python_exe = _facefusion_python(facefusion_root, python_path)
    command, effective_command_args = _build_facefusion_process_command(root, python_exe, args, skip_nsfw_check)
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "launched": False,
            "command": command,
            "effective_command_args": effective_command_args,
            "cwd": str(root),
            "skip_nsfw_check": skip_nsfw_check,
            "normalized_request": {
                "source_paths": normalized_sources,
                "target_path": target_path,
                "output_path": output_path,
                "preset": effective_preset,
                "processors": resolved["processors"],
                "execution": resolved["execution"] or {"providers": _default_provider(facefusion_root=facefusion_root, python_path=python_path)},
                "memory_options": resolved["memory_options"],
                "face_options": resolved["face_options"],
                "download_options": resolved["download_options"],
                "misc_options": normalized_misc_options or {"log_level": "info"},
                "open_browser": open_browser,
                "ui_layouts": ui_layouts or [],
                "ui_workflow": ui_workflow,
                "extra_args": resolved["extra_args"],
                "skip_nsfw_check": skip_nsfw_check,
            },
        }
    result = _launch_subprocess(command, root)
    return {
        **result,
        "dry_run": False,
        "launched": result["success"],
        "effective_command_args": effective_command_args,
        "preset": effective_preset,
        "skip_nsfw_check": skip_nsfw_check,
        "open_browser": open_browser,
        "ui_layouts": ui_layouts or [],
        "ui_workflow": ui_workflow,
    }


@mcp.tool(description="Run a batch FaceFusion workflow from file patterns.", structured_output=True)
def facefusion_batch_run(
    source_pattern: str,
    target_pattern: str,
    output_pattern: str,
    preset: str | None = None,
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
    resolved, effective_preset = _resolve_runtime_bundle(
        preset,
        defaults_bucket="tool_defaults",
        defaults_name="batch_run",
        fallback_processors=None,
        processors=processors,
        execution=execution,
        output_options=output_options,
        memory_options=memory_options,
        face_options=face_options,
        download_options=download_options,
        misc_options=misc_options,
        extra_args=extra_args,
    )
    normalized_misc_options, skip_nsfw_check = _extract_skip_nsfw_check(resolved["misc_options"])
    args = ["batch-run", "-s", source_pattern, "-t", target_pattern, "-o", output_pattern]
    args.extend(
        _build_common_run_args(
            processors=resolved["processors"],
            execution=resolved["execution"],
            output_options=resolved["output_options"],
            memory_options=resolved["memory_options"],
            face_options=resolved["face_options"],
            download_options=resolved["download_options"],
            misc_options=normalized_misc_options,
            extra_args=resolved["extra_args"],
            facefusion_root=facefusion_root,
            python_path=python_path,
            include_default_execution=True,
        )
    )
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path, skip_nsfw_check=skip_nsfw_check)
    return {
        **result,
        "patterns": {
            "source_pattern": source_pattern,
            "target_pattern": target_pattern,
            "output_pattern": output_pattern,
        },
        "preset": effective_preset,
        "skip_nsfw_check": skip_nsfw_check,
    }


@mcp.tool(description="Task shortcut: run a direct face swap on local media with sensible defaults.", structured_output=True)
def facefusion_task_face_swap(
    source_paths: list[str],
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="face_swap",
        source_paths=source_paths,
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["face_swapper", "face_enhancer"],
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
    result["task_kind"] = "face_swap"
    return result


@mcp.tool(description="Task shortcut: run a lip sync task on local media with speaking-face defaults.", structured_output=True)
def facefusion_task_lip_sync(
    source_audio_paths: list[str],
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="lip_sync",
        source_paths=source_audio_paths,
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["lip_syncer", "face_enhancer"],
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
    result["task_kind"] = "lip_sync"
    return result


@mcp.tool(description="Task shortcut: remove the background from an image or video subject.", structured_output=True)
def facefusion_task_remove_background(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="background_remove",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["background_remover"],
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
    result["task_kind"] = "background_remove"
    return result


@mcp.tool(description="Task shortcut: enhance faces in an image or video without changing identity.", structured_output=True)
def facefusion_task_enhance_face(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="face_enhance",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["face_enhancer"],
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
    result["task_kind"] = "face_enhance"
    return result


@mcp.tool(description="Task shortcut: enhance or upscale full frames for restoration work.", structured_output=True)
def facefusion_task_enhance_frame(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="frame_enhance",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["frame_enhancer"],
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
    result["task_kind"] = "frame_enhance"
    return result


@mcp.tool(description="Task shortcut: colorize grayscale or archival video frames.", structured_output=True)
def facefusion_task_colorize_frames(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="frame_colorize",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["frame_colorizer", "frame_enhancer"],
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
    result["task_kind"] = "frame_colorize"
    return result


@mcp.tool(description="Task shortcut: adjust face pose, gaze, mouth, or expression parameters.", structured_output=True)
def facefusion_task_edit_face(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="face_edit",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["face_editor"],
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
    result["task_kind"] = "face_edit"
    return result


@mcp.tool(description="Task shortcut: restore or transfer facial expression characteristics.", structured_output=True)
def facefusion_task_restore_expression(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="expression_restore",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["expression_restorer"],
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
    result["task_kind"] = "expression_restore"
    return result


@mcp.tool(description="Task shortcut: age or de-age a face in an image or video.", structured_output=True)
def facefusion_task_modify_age(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="age_modify",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["age_modifier"],
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
    result["task_kind"] = "age_modify"
    return result


@mcp.tool(description="Task shortcut: render detector, landmark, and mask overlays for debugging.", structured_output=True)
def facefusion_task_debug_faces(
    target_path: str,
    output_path: str,
    preset: str | None = None,
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
    result = _run_task_shortcut(
        task_kind="face_debug",
        source_paths=[],
        target_path=target_path,
        output_path=output_path,
        preset=preset,
        default_processors=["face_debugger"],
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
    result["task_kind"] = "face_debug"
    return result


@mcp.tool(description="Benchmark local FaceFusion providers and processor settings.", structured_output=True)
def facefusion_benchmark(
    preset: str | None = None,
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
    resolved, effective_preset = _resolve_runtime_bundle(
        preset,
        defaults_bucket="tool_defaults",
        defaults_name="benchmark",
        fallback_processors=None,
        processors=processors,
        execution=execution,
        output_options=None,
        memory_options=memory_options,
        face_options=face_options,
        download_options=None,
        misc_options=misc_options,
        extra_args=extra_args,
    )
    args = ["benchmark"]
    benchmark_rename = {
        "mode": "benchmark_mode",
        "resolutions": "benchmark_resolutions",
        "cycle_count": "benchmark_cycle_count",
        "temp_path": "temp_path",
    }
    args.extend(
        _build_common_run_args(
            processors=resolved["processors"],
            execution=resolved["execution"],
            output_options=None,
            memory_options=resolved["memory_options"],
            face_options=resolved["face_options"],
            download_options=None,
            misc_options=resolved["misc_options"],
            extra_args=None,
            facefusion_root=facefusion_root,
            python_path=python_path,
            include_default_execution=True,
        )
    )
    _append_flat_options(args, benchmark_options, benchmark_rename)
    if resolved["extra_args"]:
        args.extend(str(item) for item in resolved["extra_args"])
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path)
    return {
        **result,
        "preset": effective_preset,
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
            if not target_path or not output_path:
                raise ValueError("step_request must include target_path and output_path")
            if source_paths:
                args.extend(["-s", *source_paths])
            args.extend(["-t", target_path, "-o", output_path])
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
                include_default_execution=False,
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
    skip_nsfw_check: bool | None = None,
    background: bool = False,
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
    resolved_skip_nsfw_check = _default_skip_nsfw_check() if skip_nsfw_check is None else skip_nsfw_check
    if background:
        background_result = _launch_facefusion_background_job(
            mode=mode,
            job_id=job_id,
            jobs_path=jobs_path,
            halt_on_error=halt_on_error,
            log_level=log_level,
            skip_nsfw_check=resolved_skip_nsfw_check,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
        return background_result
    result = _run_facefusion_command(args, facefusion_root=facefusion_root, python_path=python_path, skip_nsfw_check=resolved_skip_nsfw_check)
    payload = {
        **result,
        "mode": mode,
        "job_id": job_id,
        "skip_nsfw_check": resolved_skip_nsfw_check,
    }
    if result["success"] and mode in {"run", "retry"} and job_id:
        verification = _run_multi_actor_verifier(job_id, facefusion_root=facefusion_root, python_path=python_path)
        if verification:
            payload["multi_actor_verification"] = verification
    return payload


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


@mcp.tool(description="Create or update the cast definition for a multi-actor FaceFusion project.", structured_output=True)
def facefusion_define_cast(
    project_id: str,
    target_media: list[str],
    roles: list[dict[str, Any]],
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    if not roles:
        raise ValueError("roles must not be empty")
    for media_path in target_media:
        _require_existing_file(media_path, "target_media item")
    normalized_roles = [_normalize_role(role) for role in roles]
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    _ensure_directory(project_dir / "previews")
    _ensure_directory(project_dir / "renders")
    _ensure_directory(project_dir / "manifests")
    payload = {
        "project_id": project_id,
        "target_media": target_media,
        "roles": normalized_roles,
    }
    cast_path = project_dir / "cast.json"
    _write_json(cast_path, payload)
    return {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "cast_path": str(cast_path),
        "role_count": len(normalized_roles),
        "cast": payload,
    }


@mcp.tool(description="Discover reference face clusters across planned shots before building the final multi-actor plan.", structured_output=True)
def facefusion_discover_role_references(
    project_id: str,
    sample_frames_per_shot: int = 2,
    cluster_distance_threshold: float = 0.35,
    source_hint_names: list[str] | None = None,
    project_root: str | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    if not (project_dir / "cast.json").exists():
        raise ValueError(f"Unknown project_id or missing cast.json: {project_id}")
    if not (project_dir / "shots.json").exists():
        raise ValueError(f"Unknown project_id or missing shots.json: {project_id}")
    discovery = _run_reference_discovery(
        project_id=project_id,
        sample_frames_per_shot=sample_frames_per_shot,
        cluster_distance_threshold=cluster_distance_threshold,
        source_hint_names=source_hint_names,
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    return {
        **discovery,
        "project_dir": str(project_dir),
        "references_path": str(project_dir / "references.json"),
    }


@mcp.tool(description="Apply manual merge and source prefill decisions from discovered reference clusters back into the project state.", structured_output=True)
def facefusion_apply_reference_decisions(
    project_id: str,
    groups: list[dict[str, Any]],
    overwrite_cast: bool = False,
    apply_to_empty_shot_roles: bool = True,
    skip_unassigned_groups: bool = True,
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    if not groups:
        raise ValueError("groups must not be empty")
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    references_path = project_dir / "references.json"
    cast_path = project_dir / "cast.json"
    shots_path = project_dir / "shots.json"
    references = _read_json(references_path)
    cast = _read_json(cast_path)
    shots = _read_json(shots_path)
    clusters_by_id = {cluster["cluster_id"]: cluster for cluster in references.get("clusters") or []}
    source_candidates = references.get("source_candidates") or []
    source_candidates_by_id = {candidate["candidate_id"]: candidate for candidate in source_candidates}
    merged_roles = []
    decision_groups = []
    skipped_groups = []
    for index, group in enumerate(groups, start=1):
        cluster_ids = list(group.get("cluster_ids") or [])
        if not cluster_ids:
            raise ValueError(f"group[{index}] must include cluster_ids")
        missing = [cluster_id for cluster_id in cluster_ids if cluster_id not in clusters_by_id]
        if missing:
            raise ValueError(f"group[{index}] references unknown clusters: {missing}")
        suggested_name = group.get("role_name") or group.get("suggested_role_name") or f"Role {index}"
        role_id = group.get("role_id") or _slugify(suggested_name) or f"role-{index:02d}"
        source_candidate = None
        if group.get("source_candidate_id"):
            source_candidate = source_candidates_by_id.get(group["source_candidate_id"])
        elif group.get("source_path"):
            source_candidate = {
                "candidate_id": f"manual-{index:02d}",
                "label": Path(group["source_path"]).stem,
                "source_path": group["source_path"],
            }
        else:
            first_cluster = clusters_by_id[cluster_ids[0]]
            source_candidate = first_cluster.get("prefill_source_candidate")
        if not source_candidate or not source_candidate.get("source_path"):
            if skip_unassigned_groups:
                skipped_groups.append(
                    {
                        "group_id": group.get("group_id") or f"group-{index:02d}",
                        "cluster_ids": cluster_ids,
                        "reason": "missing_source_face_path",
                    }
                )
                continue
            raise ValueError(f"group[{index}] is missing a usable source face path")
        role_payload = _normalize_role(
            {
                "role_id": role_id,
                "role_name": suggested_name,
                "source_face_path": source_candidate["source_path"],
                "source_assets": {"face": source_candidate["source_path"]},
                "notes": group.get("notes", ""),
            }
        )
        merged_roles.append(role_payload)
        decision_groups.append(
            {
                "group_id": group.get("group_id") or f"group-{index:02d}",
                "cluster_ids": cluster_ids,
                "role_id": role_id,
                "role_name": suggested_name,
                "source_candidate": source_candidate,
            }
        )
    if overwrite_cast:
        cast["roles"] = merged_roles
    else:
        existing_roles = cast.get("roles") or []
        existing_by_id = {role["role_id"]: role for role in existing_roles}
        for role in merged_roles:
            existing_by_id[role["role_id"]] = role
        cast["roles"] = list(existing_by_id.values())
    cluster_to_role_ids: dict[str, str] = {}
    for group in decision_groups:
        for cluster_id in group["cluster_ids"]:
            cluster_to_role_ids[cluster_id] = group["role_id"]
    for shot in shots.get("shots") or []:
        detected_clusters = []
        for summary in references.get("per_shot_summary") or []:
            if summary["shot_id"] == shot["shot_id"]:
                detected_clusters = list(summary.get("detected_cluster_ids") or [])
                break
        suggested_role_ids = []
        for cluster_id in detected_clusters:
            role_id = cluster_to_role_ids.get(cluster_id)
            if role_id and role_id not in suggested_role_ids:
                suggested_role_ids.append(role_id)
        shot["reference_suggested_roles"] = suggested_role_ids
        if apply_to_empty_shot_roles and not (shot.get("roles") or []):
            shot["roles"] = list(suggested_role_ids)
        if apply_to_empty_shot_roles and not (shot.get("operations") or []) and (shot.get("roles") or []):
            shot["operations"] = [
                _normalize_operation(
                    1,
                    {
                        "operation_type": "face_swap",
                        "roles": list(shot["roles"]),
                        "preview_required": shot.get("preview_required"),
                    },
                    list(shot["roles"]),
                    bool(shot.get("preview_required")),
                    shot.get("risk_level") or "medium",
                )
            ]
        if not _default_ui_mode():
            _apply_default_shot_operations_to_shot(shot)
    references["decision_groups"] = decision_groups
    _write_json(references_path, references)
    _write_json(cast_path, cast)
    _write_json(shots_path, shots)
    return {
        "project_id": project_id,
        "references_path": str(references_path),
        "cast_path": str(cast_path),
        "shots_path": str(shots_path),
        "decision_group_count": len(decision_groups),
        "skipped_group_count": len(skipped_groups),
        "skipped_groups": skipped_groups,
        "role_count": len(cast.get("roles") or []),
        "decision_groups": decision_groups,
        "cast": cast,
        "shots": shots,
    }


@mcp.tool(description="Create or update the shot list for a multi-actor FaceFusion project.", structured_output=True)
def facefusion_plan_shots(
    project_id: str,
    target_path: str | None = None,
    shots: list[dict[str, Any]] | None = None,
    time_ranges: list[dict[str, Any]] | None = None,
    auto_preview_policy: str = "smart",
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    if not shots and not time_ranges:
        raise ValueError("Provide shots or time_ranges")
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    if not project_dir.exists():
        raise ValueError(f"Unknown project_id: {project_id}")
    if shots is None:
        shots = []
        for index, item in enumerate(time_ranges or [], start=1):
            inferred_target = item.get("target_path") or target_path
            if not inferred_target:
                raise ValueError("target_path is required when time_ranges do not include target_path")
            shots.append(
                {
                    "shot_id": item.get("shot_id") or f"s{index:03d}",
                    "target_path": inferred_target,
                    "trim_start": item.get("trim_start"),
                    "trim_end": item.get("trim_end"),
                    "frame_start": item.get("frame_start"),
                    "frame_end": item.get("frame_end"),
                    "roles": item.get("roles", []),
                    "risk_level": item.get("risk_level"),
                    "preview_required": item.get("preview_required"),
                    "notes": item.get("notes", ""),
                }
            )
    normalized_shots = [_normalize_shot(index, shot, auto_preview_policy) for index, shot in enumerate(shots, start=1)]
    payload = {
        "project_id": project_id,
        "shots": normalized_shots,
    }
    shots_path = project_dir / "shots.json"
    _write_json(shots_path, payload)
    return {
        "project_id": project_id,
        "shots_path": str(shots_path),
        "shot_count": len(normalized_shots),
        "shots": payload,
    }


@mcp.tool(description="Build a preview and final task plan for a multi-actor FaceFusion project.", structured_output=True)
def facefusion_build_multi_actor_plan(
    project_id: str,
    preview_mode: str = "smart",
    quality_profile: str = "balanced",
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    cast = _read_json(project_dir / "cast.json")
    shots = _read_json(project_dir / "shots.json")
    role_ids = {role["role_id"] for role in cast["roles"]}
    tasks: list[dict[str, Any]] = []
    for shot in shots["shots"]:
        missing_roles = [role_id for role_id in shot["roles"] if role_id not in role_ids]
        if missing_roles:
            raise ValueError(f"Shot {shot['shot_id']} references unknown roles: {missing_roles}")
        for operation in shot["operations"]:
            missing_operation_roles = [role_id for role_id in operation["roles"] if role_id not in role_ids]
            if missing_operation_roles:
                raise ValueError(f"Shot {shot['shot_id']} operation references unknown roles: {missing_operation_roles}")
            profile = MULTI_ACTOR_OPERATION_PROFILES[operation["operation_type"]]
            processors = list(operation.get("processors") or profile["default_processors"])
            enhancer = profile.get("quality_enhancer")
            if enhancer and quality_profile in {"balanced", "quality"} and enhancer not in processors:
                processors.append(enhancer)
            preview_required = bool(operation["preview_required"])
            if preview_mode == "always":
                preview_required = True
            if preview_mode == "never":
                preview_required = False
            execution_provider = "cuda"
            mode = "reference" if len(operation["roles"]) > 1 and operation["operation_type"] in {"face_swap", "lip_sync"} else "standard"
            task_common = {
                "shot_id": shot["shot_id"],
                "operation_id": operation["operation_id"],
                "operation_type": operation["operation_type"],
                "roles": operation["roles"],
                "mode": mode,
                "processors": processors,
                "execution_provider": execution_provider,
                "risk_level": operation["risk_level"],
                "source_asset_kind": operation.get("source_asset_kind"),
                "source_paths": operation.get("source_paths_override") or [],
                "processor_options": operation.get("processor_options") or {},
                "face_options": operation.get("face_options") or {},
                "output_options": operation.get("output_options") or {},
                "misc_options": operation.get("misc_options") or {},
                "extra_args": operation.get("extra_args") or [],
                "notes": operation.get("notes", ""),
            }
            role_suffix = "-".join(operation["roles"]) if operation["roles"] else "global"
            operation_slug = _slugify(operation["operation_type"])
            if preview_required:
                tasks.append(
                    {
                        **task_common,
                        "task_id": f"preview-{shot['shot_id']}-{operation_slug}-{role_suffix}",
                        "task_type": "preview",
                        "status": "planned",
                        "output_path": _task_output_path(project_dir, "preview", shot["shot_id"], operation["operation_id"], operation["operation_type"], shot["target_path"]),
                        "quality_profile": "preview",
                    }
                )
            tasks.append(
                {
                    **task_common,
                    "task_id": f"final-{shot['shot_id']}-{operation_slug}-{role_suffix}",
                    "task_type": "final",
                    "status": "blocked_on_preview" if preview_required else "planned",
                    "output_path": _task_output_path(project_dir, "final", shot["shot_id"], operation["operation_id"], operation["operation_type"], shot["target_path"]),
                    "quality_profile": quality_profile,
                }
            )
    payload = {
        "project_id": project_id,
        "preview_mode": preview_mode,
        "quality_profile": quality_profile,
        "tasks": tasks,
    }
    plan_path = project_dir / "plan.json"
    _write_json(plan_path, payload)
    return {
        "project_id": project_id,
        "plan_path": str(plan_path),
        "task_count": len(tasks),
        "preview_count": len([task for task in tasks if task["task_type"] == "preview"]),
        "final_count": len([task for task in tasks if task["task_type"] == "final"]),
        "plan": payload,
    }


@mcp.tool(description="Render a standalone HTML visualization for a multi-actor FaceFusion plan.json.", structured_output=True)
def facefusion_render_plan_ui(
    project_id: str,
    output_path: str | None = None,
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    cast_path = project_dir / "cast.json"
    shots_path = project_dir / "shots.json"
    plan_path = project_dir / "plan.json"
    references_path = project_dir / "references.json"
    cast = _read_json(cast_path)
    shots = _read_json(shots_path)
    plan = _read_json(plan_path)
    references = _read_optional_json(references_path)
    view_model = _build_plan_view_model(cast, shots, plan, references=references)
    resolved_output_path = Path(output_path) if output_path else project_dir / "manifests" / "plan-view.html"
    _ensure_directory(resolved_output_path.parent)
    resolved_output_path.write_text(_render_plan_html(view_model), encoding="utf-8")
    return {
        "project_id": project_id,
        "plan_path": str(plan_path),
        "cast_path": str(cast_path),
        "shots_path": str(shots_path),
        "references_path": str(references_path) if references_path.exists() else None,
        "output_path": str(resolved_output_path),
        "view_model": view_model,
        "summary": view_model["summary"],
    }


@mcp.tool(description="Return the full current multi-actor project configuration for user confirmation before materializing or running any swap job.", structured_output=True)
def facefusion_review_multi_actor_configuration(
    project_id: str,
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    cast_path = project_dir / "cast.json"
    shots_path = project_dir / "shots.json"
    references_path = project_dir / "references.json"
    plan_path = project_dir / "plan.json"
    if not cast_path.exists():
        raise ValueError(f"Unknown project_id or missing cast.json: {project_id}")
    if not shots_path.exists():
        raise ValueError(f"Unknown project_id or missing shots.json: {project_id}")
    cast = _read_json(cast_path)
    shots = _read_json(shots_path)
    references = _read_optional_json(references_path)
    plan = _read_optional_json(plan_path)
    summary = _build_multi_actor_confirmation_summary(project_id, project_dir, cast, shots, references, plan)
    return summary


@mcp.tool(description="Render a standalone HTML visualization for discovered reference clusters and source prefills before final multi-actor planning.", structured_output=True)
def facefusion_render_reference_ui(
    project_id: str,
    output_path: str | None = None,
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    references_path = project_dir / "references.json"
    if not references_path.exists():
        raise ValueError(f"No references.json found for project_id: {project_id}")
    references = _read_json(references_path)
    shots_path = project_dir / "shots.json"
    if shots_path.exists():
        references = {**references, "shots": (_read_json(shots_path).get("shots") or [])}
    references = {
        **references,
        "multi_actor_defaults": _default_multi_actor_defaults(),
        "default_choices": _available_choice_catalog(facefusion_root=facefusion_root, python_path=None),
        "current_env_config": _read_env_config(),
        "env_config_path": str(ENV_CONFIG_PATH),
    }
    resolved_output_path = Path(output_path) if output_path else project_dir / "manifests" / "reference-view.html"
    _ensure_directory(resolved_output_path.parent)
    resolved_output_path.write_text(_render_reference_html(references), encoding="utf-8")
    return {
        "project_id": project_id,
        "references_path": str(references_path),
        "output_path": str(resolved_output_path),
        "references": references,
        "cluster_count": len(references.get("clusters") or []),
        "group_count": len(references.get("decision_groups") or references.get("suggested_groups") or []),
    }


@mcp.tool(description="Apply optional per-shot pipeline operations such as lip sync, face enhancement, frame enhancement, background removal, expression restore, face edit, age modify, or colorization back into shots.json before plan build.", structured_output=True)
def facefusion_apply_shot_operation_decisions(
    project_id: str,
    shot_operations: list[dict[str, Any]],
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    if not shot_operations:
        raise ValueError("shot_operations must not be empty")
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    shots_path = project_dir / "shots.json"
    shots_payload = _read_json(shots_path)
    shots = shots_payload.get("shots") or []
    shots_by_id = {shot["shot_id"]: shot for shot in shots}
    updated_shots = []
    for item in shot_operations:
        shot_id = item.get("shot_id")
        if not shot_id or shot_id not in shots_by_id:
            raise ValueError(f"Unknown shot_id in shot_operations: {shot_id}")
        shot = shots_by_id[shot_id]
        enabled_operations = list(dict.fromkeys(item.get("enabled_operations") or []))
        shot["operations"] = _shot_operation_decision_to_operations(shot, enabled_operations)
        if item.get("notes"):
            existing_notes = shot.get("notes", "")
            shot["notes"] = f"{existing_notes} | {item['notes']}".strip(" |")
        updated_shots.append(
            {
                "shot_id": shot_id,
                "enabled_operations": enabled_operations,
                "operation_types": [operation.get("operation_type") for operation in shot.get("operations") or []],
                "operation_count": len(shot.get("operations") or []),
            }
        )
    _write_json(shots_path, shots_payload)
    return {
        "project_id": project_id,
        "shots_path": str(shots_path),
        "updated_shot_count": len(updated_shots),
        "updated_shots": updated_shots,
        "shots": shots_payload,
    }


@mcp.tool(description="Create FaceFusion jobs and steps from a multi-actor project plan.", structured_output=True)
def facefusion_materialize_multi_actor_jobs(
    project_id: str,
    job_strategy: str = "per_project",
    include_final_tasks: bool = False,
    jobs_path: str | None = None,
    log_level: str = "info",
    project_root: str | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    cast = _read_json(project_dir / "cast.json")
    shots = _read_json(project_dir / "shots.json")
    plan = _read_json(project_dir / "plan.json")
    roles_by_id = {role["role_id"]: role for role in cast["roles"]}
    shots_by_id = {shot["shot_id"]: shot for shot in shots["shots"]}
    if job_strategy != "per_project":
        raise ValueError("Only job_strategy='per_project' is currently supported")
    job_id = project_id
    create_result = facefusion_create_job(
        job_id=job_id,
        jobs_path=jobs_path,
        log_level=log_level,
        facefusion_root=facefusion_root,
        python_path=python_path,
    )
    if not create_result["success"]:
        return {
            "project_id": project_id,
            "job_id": job_id,
            "created": False,
            "create_result": create_result,
            "steps_created": [],
        }
    steps_created = []
    next_job_step_index = 0
    for task in plan["tasks"]:
        if task["task_type"] == "final" and not include_final_tasks:
            continue
        shot = shots_by_id[task["shot_id"]]
        step_requests = _build_task_step_requests(task, shot, roles_by_id, project_dir, job_id, overwrite=False)
        add_results = []
        all_steps_succeeded = True
        for step_index, step_request in enumerate(step_requests, start=1):
            add_result = facefusion_update_job_steps(
                action="add",
                job_id=job_id,
                step_request=step_request,
                jobs_path=jobs_path,
                log_level=log_level,
                facefusion_root=facefusion_root,
                python_path=python_path,
            )
            add_results.append(
                {
                    "step_index": step_index,
                    "job_step_index": next_job_step_index,
                    "step_request": step_request,
                    "result": add_result,
                }
            )
            next_job_step_index += 1
            if not add_result["success"]:
                all_steps_succeeded = False
                break
        steps_created.append(
            {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "step_count": len(step_requests),
                "results": add_results,
            }
        )
        if all_steps_succeeded:
            _set_task_status(
                task,
                "materialized",
                note="Task added to FaceFusion job queue.",
                materialized_job_id=job_id,
                last_materialization_success=True,
                materialized_step_count=len(step_requests),
            )
        else:
            failed_result = add_results[-1]["result"] if add_results else {}
            _set_task_status(
                task,
                "materialize_failed",
                note=failed_result.get("stderr_summary") or failed_result.get("stdout_summary") or "Materialization failed.",
                materialized_job_id=job_id,
                last_materialization_success=False,
                materialized_step_count=len(add_results),
            )
    _write_json(project_dir / "plan.json", plan)
    manifest_path = project_dir / "manifests" / "materialized-job.json"
    _write_json(
        manifest_path,
        {
            "project_id": project_id,
            "job_id": job_id,
            "include_final_tasks": include_final_tasks,
            "steps_created": steps_created,
        },
    )
    return {
        "project_id": project_id,
        "job_id": job_id,
        "created": True,
        "steps_created": steps_created,
        "manifest_path": str(manifest_path),
    }


@mcp.tool(description="Approve or reject a preview task and unlock or keep-blocked the matching final task.", structured_output=True)
def facefusion_approve_preview(
    project_id: str,
    task_id: str | None = None,
    shot_id: str | None = None,
    approved: bool = True,
    approval_notes: str = "",
    project_root: str | None = None,
    facefusion_root: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    plan_path = project_dir / "plan.json"
    plan = _read_json(plan_path)
    if not task_id and not shot_id:
        raise ValueError("Provide task_id or shot_id")
    preview_task: dict[str, Any] | None = None
    if task_id:
        candidate = _find_task(plan, task_id)
        if candidate["task_type"] != "preview":
            raise ValueError("task_id must reference a preview task")
        preview_task = candidate
    else:
        preview_matches = [
            task
            for task in plan["tasks"]
            if task["task_type"] == "preview" and task["shot_id"] == shot_id
        ]
        if len(preview_matches) > 1:
            raise ValueError(f"Multiple preview tasks found for shot_id '{shot_id}'. Use task_id instead.")
        for task in plan["tasks"]:
            if task["task_type"] == "preview" and task["shot_id"] == shot_id:
                preview_task = task
                break
        if preview_task is None:
            raise ValueError(f"No preview task found for shot_id: {shot_id}")
    matching_final_tasks = [
        task
        for task in plan["tasks"]
        if task["task_type"] == "final"
        and task["shot_id"] == preview_task["shot_id"]
        and task.get("operation_id") == preview_task.get("operation_id")
    ]
    if approved:
        _set_task_status(preview_task, "approved", note=approval_notes or "Preview approved.")
        for task in matching_final_tasks:
            if task["status"] in {"blocked_on_preview", "blocked_on_revision"}:
                _set_task_status(task, "planned", note="Preview approved; final task unlocked.")
    else:
        _set_task_status(preview_task, "rejected", note=approval_notes or "Preview rejected.")
        for task in matching_final_tasks:
            _set_task_status(task, "blocked_on_revision", note="Preview rejected; revise before final render.")
    _write_json(plan_path, plan)
    return {
        "project_id": project_id,
        "preview_task_id": preview_task["task_id"],
        "preview_status": preview_task["status"],
        "final_tasks": [
            {"task_id": task["task_id"], "status": task["status"]}
            for task in matching_final_tasks
        ],
        "plan_path": str(plan_path),
    }


@mcp.tool(description="Reset a failed multi-actor task for retry, and optionally materialize it into a dedicated retry job.", structured_output=True)
def facefusion_retry_failed_task(
    project_id: str,
    task_id: str,
    materialize_immediately: bool = False,
    jobs_path: str | None = None,
    log_level: str = "info",
    project_root: str | None = None,
    facefusion_root: str | None = None,
    python_path: str | None = None,
) -> dict[str, Any]:
    project_dir = _project_dir(project_id, project_root=project_root, facefusion_root=facefusion_root)
    plan_path = project_dir / "plan.json"
    plan = _read_json(plan_path)
    cast = _read_json(project_dir / "cast.json")
    shots = _read_json(project_dir / "shots.json")
    task = _find_task(plan, task_id)
    allowed_statuses = {"materialize_failed", "failed", "rejected", "blocked_on_revision"}
    if task["status"] not in allowed_statuses:
        raise ValueError(f"Task {task_id} is not in a retryable state: {task['status']}")
    retry_count = int(task.get("retry_count", 0)) + 1
    task["retry_count"] = retry_count
    _set_task_status(task, "planned", note="Task reset for retry.")
    roles_by_id = {role["role_id"]: role for role in cast["roles"]}
    shots_by_id = {shot["shot_id"]: shot for shot in shots["shots"]}
    materialization_result = None
    if materialize_immediately:
        retry_job_id = f"{project_id}-retry-{_slugify(task_id)}-{retry_count}"
        create_result = facefusion_create_job(
            job_id=retry_job_id,
            jobs_path=jobs_path,
            log_level=log_level,
            facefusion_root=facefusion_root,
            python_path=python_path,
        )
        materialization_result = {"create_result": create_result}
        if create_result["success"]:
            shot = shots_by_id[task["shot_id"]]
            step_requests = _build_task_step_requests(task, shot, roles_by_id, project_dir, retry_job_id, overwrite=False)
            add_results = []
            all_steps_succeeded = True
            for step_request in step_requests:
                add_result = facefusion_update_job_steps(
                    action="add",
                    job_id=retry_job_id,
                    step_request=step_request,
                    jobs_path=jobs_path,
                    log_level=log_level,
                    facefusion_root=facefusion_root,
                    python_path=python_path,
                )
                add_results.append(add_result)
                if not add_result["success"]:
                    all_steps_succeeded = False
                    break
            materialization_result["add_results"] = add_results
            if all_steps_succeeded:
                _set_task_status(
                    task,
                    "materialized",
                    note="Retry task materialized into a dedicated retry job.",
                    materialized_job_id=retry_job_id,
                    last_materialization_success=True,
                )
            else:
                failed_result = add_results[-1] if add_results else {}
                _set_task_status(
                    task,
                    "materialize_failed",
                    note=failed_result.get("stderr_summary") or failed_result.get("stdout_summary") or "Retry materialization failed.",
                    materialized_job_id=retry_job_id,
                    last_materialization_success=False,
                )
        else:
            _set_task_status(
                task,
                "materialize_failed",
                note=create_result.get("stderr_summary") or create_result.get("stdout_summary") or "Retry job creation failed.",
                last_materialization_success=False,
            )
    _write_json(plan_path, plan)
    return {
        "project_id": project_id,
        "task_id": task_id,
        "status": task["status"],
        "retry_count": retry_count,
        "materialize_immediately": materialize_immediately,
        "materialization_result": materialization_result,
        "plan_path": str(plan_path),
    }


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


@mcp.resource("facefusion://recipes/multi-actor-workflow", name="facefusion-multi-actor-workflow", description="Project-state workflow for multi-role and multi-face FaceFusion edits.")
def resource_multi_actor_workflow() -> str:
    return (RESOURCE_DIR / "multi-actor-workflow.md").read_text(encoding="utf-8")


@mcp.prompt(name="run-facefusion-task", description="Route a normal media-processing request into the right FaceFusion tool sequence.")
def prompt_run_facefusion_task() -> str:
    ui_mode = _default_ui_mode()
    return "".join(
        [
            "Use FaceFusion Local to fulfill a direct media-processing request. ",
            "First decide whether the user wants a single task or a pattern-based batch. ",
            "If environment readiness is unknown, call facefusion_health_check. ",
            "If the task is missing models or looks like a first run, call facefusion_download_models. ",
            "Use facefusion://reference/processors and facefusion://recipes/common-workflows to choose processors. ",
            (
                "The environment prefers UI mode by default, so when the request becomes multi-step or benefits from review, generate the initial draft state and render the relevant UI before continuing follow-up questions. "
                if ui_mode
                else "The environment prefers no-UI mode by default, so generate the initial draft state first and then continue by follow-up dialogue without requiring the user to use the HTML review pages. "
            ),
            "Then call facefusion_run_job for one task or facefusion_batch_run for a batch. ",
            "Do not use job-management tools unless the user explicitly wants a queue or drafts.",
        ]
    )


@mcp.prompt(name="prepare-facefusion-environment", description="Prepare the local FaceFusion environment before larger tasks.")
def prompt_prepare_facefusion_environment() -> str:
    return (
        "Prepare the local FaceFusion environment. "
        "Start with facefusion_health_check. "
        "If FaceFusion is missing or not fully set up, explain the missing components and ask for explicit confirmation before calling facefusion_install_or_setup. "
        "If the user asks what is available, call facefusion_list_capabilities. "
        "If models are missing or the user wants a preload, call facefusion_download_models. "
        "If the user asks about performance or provider choice, call facefusion_benchmark. "
        "Do not launch processing jobs in this workflow unless the user explicitly pivots into a run request."
    )


@mcp.prompt(name="orchestrate-facefusion-jobs", description="Build and operate drafted, queued, or retried FaceFusion jobs.")
def prompt_orchestrate_facefusion_jobs() -> str:
    ui_mode = _default_ui_mode()
    return "".join(
        [
            "Use FaceFusion job tools for queue-oriented workflows. ",
            "For multi-actor workflows, first use facefusion_define_cast, facefusion_plan_shots, facefusion_discover_role_references, facefusion_apply_reference_decisions, facefusion_apply_shot_operation_decisions when needed, and facefusion_build_multi_actor_plan, then use facefusion_materialize_multi_actor_jobs. ",
            (
                "Because UI mode is the default in this environment, after the initial project draft is generated you should normally render reference-view.html and plan-view.html so the user can refine cast, merge, source, and shot-operation details visually, while still continuing the conversation to fill gaps. "
                if ui_mode
                else "Because no-UI mode is the default in this environment, after the initial project draft is generated you should continue by summarizing the current cast, references, optional shot operations, and plan state in conversation and asking focused follow-up questions until the missing details are filled. "
            ),
            "Use facefusion_approve_preview to promote approved preview tasks into final work, and use facefusion_retry_failed_task for local recovery on only the affected task. ",
            "Otherwise create a draft with facefusion_create_job, then use facefusion_update_job_steps to add, insert, remix, or remove steps. ",
            "Inspect the queue with facefusion_manage_jobs. ",
            "Submit, run, or retry jobs with facefusion_run_jobs. ",
            "Prefer this path only when the user wants drafts, queues, retries, or step-by-step orchestration.",
        ]
    )


@mcp.prompt(name="diagnose-facefusion-failure", description="Diagnose a failed FaceFusion task or environment issue.")
def prompt_diagnose_facefusion_failure() -> str:
    return (
        "Diagnose a FaceFusion failure. "
        "Start from the failing tool result and summarize the concrete error. "
        "Read facefusion://reference/troubleshooting for likely causes and recovery paths. "
        "For multi-actor project failures, prefer facefusion_retry_failed_task over rebuilding the entire queue, and use facefusion_approve_preview when a preview should keep final work blocked. "
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
