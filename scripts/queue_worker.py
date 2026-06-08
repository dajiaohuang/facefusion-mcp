from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facefusion-root", required=True)
    parser.add_argument("--python-path", required=True)
    parser.add_argument("--state-path", required=True)
    parser.add_argument("--log-level", default="info")
    parser.add_argument("--jobs-path")
    parser.add_argument("--skip-nsfw-check", action="store_true")
    parser.add_argument("--idle-grace-seconds", type=float, default=2.0)
    return parser.parse_args()


def write_state(state_path: Path, payload: dict[str, object]) -> None:
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clear_state_if_owned(state_path: Path) -> None:
    try:
        current = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        current = {}
    if int(current.get("pid", 0) or 0) == os.getpid():
        try:
            state_path.unlink(missing_ok=True)
        except OSError:
            pass


def build_facefusion_command(python_path: str, facefusion_root: str, command_args: list[str], skip_nsfw_check: bool) -> list[str]:
    effective_argv = ["facefusion.py", *command_args]
    if skip_nsfw_check:
        argv_literal = repr(effective_argv)
        injected = (
            f"import runpy, sys; sys.path.insert(0, r'{facefusion_root}'); "
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
        return [python_path, "-c", injected]
    return [python_path, "facefusion.py", *command_args]


def run_facefusion(facefusion_root: str, python_path: str, command_args: list[str], skip_nsfw_check: bool) -> subprocess.CompletedProcess[str]:
    command = build_facefusion_command(python_path, facefusion_root, command_args, skip_nsfw_check)
    return subprocess.run(
        command,
        cwd=facefusion_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def list_queued_job_ids(facefusion_root: str, jobs_path: str | None) -> list[str]:
    jobs_root = Path(jobs_path) if jobs_path else Path(facefusion_root) / ".jobs"
    queued_dir = jobs_root / "queued"
    if not queued_dir.exists():
        return []
    return sorted(path.stem for path in queued_dir.glob("*.json"))


def run_multi_actor_verifier(facefusion_root: str, python_path: str, job_id: str) -> subprocess.CompletedProcess[str]:
    verifier_script = Path(__file__).with_name("multi_actor_verify.py")
    return subprocess.run(
        [
            python_path,
            str(verifier_script),
            "--facefusion-root",
            facefusion_root,
            "--job-id",
            job_id,
        ],
        cwd=facefusion_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def queued_job_count(facefusion_root: str, python_path: str, jobs_path: str | None, log_level: str) -> int:
    args = ["job-list", "queued", "--log-level", log_level]
    if jobs_path:
        args.extend(["--jobs-path", jobs_path])
    completed = run_facefusion(facefusion_root, python_path, args, skip_nsfw_check=False)
    text = (completed.stdout or "") + (completed.stderr or "")
    rows = [
        line for line in text.splitlines()
        if line.strip().startswith("|") and "job id" not in line.lower()
    ]
    return len(rows)


def main() -> int:
    args = parse_args()
    state_path = Path(args.state_path)
    write_state(
        state_path,
        {
            "pid": os.getpid(),
            "started_at": time.time(),
            "facefusion_root": args.facefusion_root,
            "jobs_path": args.jobs_path,
            "status": "running",
        },
    )
    try:
        idle_seen_at: float | None = None
        while True:
            queued_count = queued_job_count(args.facefusion_root, args.python_path, args.jobs_path, args.log_level)
            if queued_count <= 0:
                if idle_seen_at is None:
                    idle_seen_at = time.time()
                elif time.time() - idle_seen_at >= args.idle_grace_seconds:
                    return 0
                time.sleep(0.5)
                continue

            idle_seen_at = None
            queued_job_ids = list_queued_job_ids(args.facefusion_root, args.jobs_path)
            run_args = ["job-run-all", "--log-level", args.log_level]
            if args.jobs_path:
                run_args.extend(["--jobs-path", args.jobs_path])
            completed = run_facefusion(args.facefusion_root, args.python_path, run_args, skip_nsfw_check=args.skip_nsfw_check)
            if completed.returncode != 0:
                write_state(
                    state_path,
                    {
                        "pid": os.getpid(),
                        "started_at": time.time(),
                        "facefusion_root": args.facefusion_root,
                        "jobs_path": args.jobs_path,
                        "status": "error",
                        "return_code": completed.returncode,
                        "stderr_tail": (completed.stderr or "")[-4000:],
                    },
                )
                return completed.returncode
            verification_failures: list[dict[str, object]] = []
            for job_id in queued_job_ids:
                verification = run_multi_actor_verifier(args.facefusion_root, args.python_path, job_id)
                if verification.returncode != 0:
                    verification_failures.append(
                        {
                            "job_id": job_id,
                            "stdout_tail": (verification.stdout or "")[-2000:],
                            "stderr_tail": (verification.stderr or "")[-2000:],
                        }
                    )
            if verification_failures:
                write_state(
                    state_path,
                    {
                        "pid": os.getpid(),
                        "started_at": time.time(),
                        "facefusion_root": args.facefusion_root,
                        "jobs_path": args.jobs_path,
                        "status": "verification_warning",
                        "verification_failures": verification_failures,
                    },
                )
            time.sleep(0.5)
    finally:
        clear_state_if_owned(state_path)


if __name__ == "__main__":
    raise SystemExit(main())
