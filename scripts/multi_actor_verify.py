from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facefusion-root", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--diff-threshold", type=float, default=0.035)
    parser.add_argument("--distance-margin", type=float, default=0.015)
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_project_dir(facefusion_root: Path, job_id: str) -> Path | None:
    projects_root = facefusion_root / ".multi-actor-projects"
    if not projects_root.exists():
        return None
    for plan_path in projects_root.glob("*/plan.json"):
        try:
            plan = _read_json(plan_path)
        except (OSError, json.JSONDecodeError):
            continue
        for task in plan.get("tasks", []):
            if task.get("materialized_job_id") == job_id:
                return plan_path.parent
    return None


def _find_job_file(facefusion_root: Path, job_id: str) -> tuple[str | None, Path | None]:
    jobs_root = facefusion_root / ".jobs"
    for status in ("completed", "failed", "queued", "drafted"):
        candidate = jobs_root / status / f"{job_id}.json"
        if candidate.exists():
            return status, candidate
    return None, None


def _set_face_state(step_args: dict[str, Any]) -> None:
    import facefusion.choices
    from facefusion import state_manager

    defaults = {
        "face_detector_model": "yolo_face",
        "face_detector_size": "640x640",
        "face_detector_margin": [0, 0, 0, 0],
        "face_detector_angles": [0],
        "face_detector_score": 0.5,
        "face_landmarker_model": "2dfan4",
        "face_landmarker_score": 0.5,
        "face_selector_order": "left-right",
        "face_selector_gender": None,
        "face_selector_race": None,
        "face_selector_age_start": None,
        "face_selector_age_end": None,
        "download_providers": list(facefusion.choices.download_providers),
        "execution_providers": ["cpu"],
        "execution_device_ids": [0],
        "execution_thread_count": 1,
    }
    for key, default_value in defaults.items():
        state_manager.init_item(key, step_args.get(key, default_value))


def _read_frame(media_path: str, frame_number: int):
    import cv2

    path = Path(media_path)
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return cv2.imread(str(path), cv2.IMREAD_COLOR)
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return None
        capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_number))
        ok, frame = capture.read()
        if ok:
            return frame
        return None
    finally:
        capture.release()


def _count_frames(media_path: str) -> int:
    import cv2

    path = Path(media_path)
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return 1
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return 0
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()


def _sample_relative_frames(frame_total: int, sample_count: int) -> list[int]:
    if frame_total <= 1:
        return [0]
    sample_count = max(1, sample_count)
    if sample_count == 1:
        return [frame_total // 2]
    samples: list[int] = []
    for index in range(sample_count):
        ratio = (index + 1) / (sample_count + 1)
        samples.append(min(frame_total - 1, max(0, int(round((frame_total - 1) * ratio)))))
    return sorted(set(samples))


def _crop_with_padding(frame, bounding_box, padding_ratio: float = 0.25):
    import numpy

    height, width = frame.shape[:2]
    left, top, right, bottom = [int(round(value)) for value in bounding_box]
    box_width = max(1, right - left)
    box_height = max(1, bottom - top)
    pad_x = int(math.ceil(box_width * padding_ratio))
    pad_y = int(math.ceil(box_height * padding_ratio))
    crop_left = max(0, left - pad_x)
    crop_top = max(0, top - pad_y)
    crop_right = min(width, right + pad_x)
    crop_bottom = min(height, bottom + pad_y)
    crop = frame[crop_top:crop_bottom, crop_left:crop_right]
    return crop if numpy.any(crop) else None


def _resize_like(source_frame, target_frame):
    import cv2

    if source_frame.shape[:2] == target_frame.shape[:2]:
        return source_frame
    return cv2.resize(source_frame, (target_frame.shape[1], target_frame.shape[0]), interpolation=cv2.INTER_AREA)


def _write_image(image_path: Path, frame) -> None:
    from facefusion.vision import write_image

    write_image(str(image_path), frame)


def _verify_face_swap_step(
    step_args: dict[str, Any],
    step_meta: dict[str, Any],
    verification_dir: Path,
    sample_count: int,
    diff_threshold: float,
    distance_margin: float,
) -> dict[str, Any]:
    import cv2
    import numpy
    from facefusion.face_analyser import get_many_faces
    from facefusion.face_selector import calculate_face_distance, sort_faces_by_order

    _set_face_state(step_args)
    source_paths = step_args.get("source_paths") or []
    if not source_paths:
        return {"applicable": False, "reason": "missing_source"}
    source_frame = _read_frame(source_paths[0], 0)
    if source_frame is None:
        return {"applicable": False, "reason": "source_read_failed"}
    source_faces = sort_faces_by_order(get_many_faces([source_frame]), "large-small")
    if not source_faces:
        return {"applicable": False, "reason": "source_face_not_detected"}
    source_face = source_faces[0]

    before_path = step_args.get("target_path")
    after_path = step_args.get("output_path")
    if not before_path or not after_path or not Path(after_path).exists():
        return {"applicable": False, "reason": "missing_before_or_after_output"}

    selector_order = step_args.get("face_selector_order") or "left-right"
    reference_position = int(step_args.get("reference_face_position", 0) or 0)
    trim_start = int(step_args.get("trim_frame_start", 0) or 0)
    trim_end = step_args.get("trim_frame_end")
    after_frame_total = _count_frames(after_path)
    if after_frame_total <= 0:
        return {"applicable": False, "reason": "after_frame_count_zero"}

    effective_after_total = after_frame_total
    relative_frames = _sample_relative_frames(effective_after_total, sample_count)
    before_total = _count_frames(before_path)
    before_offset = trim_start if trim_start > 0 and before_total > after_frame_total else 0

    samples: list[dict[str, Any]] = []
    passed_samples = 0
    valid_samples = 0
    representative_after = None
    representative_before = None

    for sample_index, relative_frame in enumerate(relative_frames, start=1):
        before_frame_number = min(max(0, before_offset + relative_frame), max(0, before_total - 1))
        after_frame_number = min(max(0, relative_frame), max(0, after_frame_total - 1))
        before_frame = _read_frame(before_path, before_frame_number)
        after_frame = _read_frame(after_path, after_frame_number)
        sample_payload: dict[str, Any] = {
            "sample_index": sample_index,
            "relative_frame": relative_frame,
            "before_frame": before_frame_number,
            "after_frame": after_frame_number,
        }
        if before_frame is None or after_frame is None:
            sample_payload["status"] = "frame_read_failed"
            samples.append(sample_payload)
            continue

        before_faces = sort_faces_by_order(get_many_faces([before_frame]), selector_order)
        after_faces = sort_faces_by_order(get_many_faces([after_frame]), selector_order)
        if reference_position >= len(before_faces) or reference_position >= len(after_faces):
            sample_payload["status"] = "face_slot_missing"
            sample_payload["before_face_count"] = len(before_faces)
            sample_payload["after_face_count"] = len(after_faces)
            samples.append(sample_payload)
            continue

        before_face = before_faces[reference_position]
        after_face = after_faces[reference_position]
        before_crop = _crop_with_padding(before_frame, before_face.bounding_box)
        after_crop = _crop_with_padding(after_frame, after_face.bounding_box)
        if before_crop is None or after_crop is None:
            sample_payload["status"] = "crop_failed"
            samples.append(sample_payload)
            continue

        valid_samples += 1
        before_crop_resized = _resize_like(before_crop, after_crop)
        diff_frame = cv2.absdiff(before_crop_resized, after_crop)
        crop_diff_mean = float(numpy.mean(diff_frame) / 255.0)
        before_distance = float(calculate_face_distance(before_face, source_face))
        after_distance = float(calculate_face_distance(after_face, source_face))
        distance_improvement = before_distance - after_distance
        passed = (
            (crop_diff_mean >= diff_threshold and distance_improvement >= distance_margin)
            or (crop_diff_mean >= diff_threshold * 0.7 and distance_improvement >= max(distance_margin, 0.3))
        )
        if passed:
            passed_samples += 1
        sample_payload.update(
            {
                "status": "verified" if passed else "no_strong_evidence",
                "crop_diff_mean": crop_diff_mean,
                "before_to_source_distance": before_distance,
                "after_to_source_distance": after_distance,
                "distance_improvement": distance_improvement,
                "passed": passed,
            }
        )

        base_name = (
            f"step-{step_meta.get('job_step_index', 0):02d}"
            f"-{step_meta.get('role_id', 'role')}"
            f"-sample-{sample_index:02d}"
        )
        before_crop_path = verification_dir / f"{base_name}-before.png"
        after_crop_path = verification_dir / f"{base_name}-after.png"
        diff_crop_path = verification_dir / f"{base_name}-diff.png"
        _write_image(before_crop_path, before_crop)
        _write_image(after_crop_path, after_crop)
        _write_image(diff_crop_path, diff_frame)
        sample_payload["before_crop_path"] = str(before_crop_path)
        sample_payload["after_crop_path"] = str(after_crop_path)
        sample_payload["diff_crop_path"] = str(diff_crop_path)

        if representative_after is None:
            representative_after = after_frame
            representative_before = before_frame

        samples.append(sample_payload)

    overall_passed = valid_samples > 0 and passed_samples >= math.ceil(valid_samples / 2)
    if representative_before is not None and representative_after is not None:
        frame_base = f"step-{step_meta.get('job_step_index', 0):02d}-{step_meta.get('role_id', 'role')}"
        before_frame_path = verification_dir / f"{frame_base}-before-frame.png"
        after_frame_path = verification_dir / f"{frame_base}-after-frame.png"
        _write_image(before_frame_path, representative_before)
        _write_image(after_frame_path, representative_after)
    else:
        before_frame_path = None
        after_frame_path = None

    return {
        "applicable": True,
        "operation_type": "face_swap",
        "role_id": step_meta.get("role_id"),
        "job_step_index": step_meta.get("job_step_index"),
        "reference_face_position": reference_position,
        "selector_order": selector_order,
        "sample_count": len(relative_frames),
        "valid_sample_count": valid_samples,
        "passed_sample_count": passed_samples,
        "passed": overall_passed,
        "thresholds": {
            "crop_diff_mean": diff_threshold,
            "distance_improvement": distance_margin,
        },
        "samples": samples,
        "representative_before_frame_path": str(before_frame_path) if before_frame_path else None,
        "representative_after_frame_path": str(after_frame_path) if after_frame_path else None,
    }


def verify_job(facefusion_root: Path, job_id: str, sample_count: int, diff_threshold: float, distance_margin: float) -> dict[str, Any]:
    project_dir = _find_project_dir(facefusion_root, job_id)
    if project_dir is None:
        return {"success": False, "job_id": job_id, "reason": "project_not_found"}

    manifest_path = project_dir / "manifests" / "materialized-job.json"
    plan_path = project_dir / "plan.json"
    if not manifest_path.exists() or not plan_path.exists():
        return {"success": False, "job_id": job_id, "reason": "manifest_or_plan_missing"}

    job_status, job_file = _find_job_file(facefusion_root, job_id)
    if job_file is None:
        return {"success": False, "job_id": job_id, "reason": "job_file_not_found"}

    materialized = _read_json(manifest_path)
    plan = _read_json(plan_path)
    job_payload = _read_json(job_file)
    verification_dir = project_dir / "manifests" / "verification" / job_id
    verification_dir.mkdir(parents=True, exist_ok=True)

    task_index = {
        task.get("task_id"): task
        for task in plan.get("tasks", [])
    }
    job_steps = job_payload.get("steps", [])
    materialized_output_paths: dict[int, str] = {}
    for task_entry in materialized.get("steps_created", []):
        for step_result in task_entry.get("results", []):
            job_step_index = int(step_result.get("job_step_index", 0))
            step_request = step_result.get("step_request") or {}
            output_path = step_request.get("output_path")
            if output_path:
                materialized_output_paths[job_step_index] = output_path
    global_step_counter = 0
    task_reports: list[dict[str, Any]] = []

    for task_entry in materialized.get("steps_created", []):
        task_id = task_entry.get("task_id")
        task_report = {
            "task_id": task_id,
            "task_type": task_entry.get("task_type"),
            "step_reports": [],
        }
        for step_result in task_entry.get("results", []):
            step_meta = dict(step_result.get("step_request") or {})
            step_meta["job_step_index"] = step_result.get("job_step_index", global_step_counter)
            global_index = int(step_meta["job_step_index"])
            global_step_counter = global_index + 1
            if global_index >= len(job_steps):
                task_report["step_reports"].append(
                    {
                        "job_step_index": global_index,
                        "applicable": False,
                        "reason": "job_step_missing",
                    }
                )
                continue
            step_args = job_steps[global_index].get("args") or {}
            step_status = job_steps[global_index].get("status")
            if "face_swapper" not in (step_args.get("processors") or []):
                task_report["step_reports"].append(
                    {
                        "job_step_index": global_index,
                        "applicable": False,
                        "reason": "not_face_swapper_step",
                        "step_status": step_status,
                    }
                )
                continue
            if step_status != "completed":
                task_report["step_reports"].append(
                    {
                        "job_step_index": global_index,
                        "applicable": False,
                        "reason": "step_not_completed",
                        "step_status": step_status,
                    }
                )
                continue
            effective_step_args = dict(step_args)
            target_path = effective_step_args.get("target_path")
            if (not target_path or not Path(target_path).exists()) and global_index > 0:
                previous_output_path = materialized_output_paths.get(global_index - 1)
                if previous_output_path and Path(previous_output_path).exists():
                    effective_step_args["target_path"] = previous_output_path
            report = _verify_face_swap_step(
                step_args=effective_step_args,
                step_meta=step_meta,
                verification_dir=verification_dir,
                sample_count=sample_count,
                diff_threshold=diff_threshold,
                distance_margin=distance_margin,
            )
            report["step_status"] = step_status
            task_report["step_reports"].append(report)

        applicable_reports = [report for report in task_report["step_reports"] if report.get("applicable")]
        task_report["verification_passed"] = bool(applicable_reports) and all(report.get("passed") for report in applicable_reports)
        task_reports.append(task_report)
        task = task_index.get(task_id)
        if task is not None:
            task["step_verifications"] = task_report["step_reports"]
            task["verification_passed"] = task_report["verification_passed"]
            task["verification_summary"] = (
                f"{sum(1 for report in applicable_reports if report.get('passed'))}/{len(applicable_reports)} "
                "face-swap steps passed sampled verification."
                if applicable_reports else "No applicable sampled verification reports."
            )

    report_payload = {
        "success": True,
        "job_id": job_id,
        "job_status": job_status,
        "project_id": plan.get("project_id"),
        "project_dir": str(project_dir),
        "task_reports": task_reports,
    }
    report_path = project_dir / "manifests" / f"verification-{job_id}.json"
    _write_json(report_path, report_payload)
    plan["last_verification"] = {
        "job_id": job_id,
        "job_status": job_status,
        "report_path": str(report_path),
    }
    _write_json(plan_path, plan)
    report_payload["report_path"] = str(report_path)
    report_payload["plan_path"] = str(plan_path)
    return report_payload


def main() -> int:
    args = parse_args()
    facefusion_root = Path(args.facefusion_root)
    if str(facefusion_root) not in sys.path:
        sys.path.insert(0, str(facefusion_root))
    try:
        payload = verify_job(
            facefusion_root=facefusion_root,
            job_id=args.job_id,
            sample_count=args.sample_count,
            diff_threshold=args.diff_threshold,
            distance_margin=args.distance_margin,
        )
        print(json.dumps(payload, ensure_ascii=False))
        return 0 if payload.get("success") else 1
    except Exception as exc:  # pragma: no cover - CLI fallback
        print(json.dumps({"success": False, "job_id": args.job_id, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
