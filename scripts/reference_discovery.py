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
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--sample-frames-per-shot", type=int, default=2)
    parser.add_argument("--cluster-distance-threshold", type=float, default=0.35)
    parser.add_argument("--source-hint-names", nargs="*")
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slugify(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _ensure_face_state() -> None:
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
    for key, value in defaults.items():
        state_manager.init_item(key, value)


def _frame_count(video_path: str) -> int:
    import cv2

    capture = cv2.VideoCapture(video_path)
    try:
        if not capture.isOpened():
            return 0
        return int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()


def _sample_frames(frame_start: int, frame_end: int, sample_count: int) -> list[int]:
    sample_count = max(1, sample_count)
    if frame_end <= frame_start:
        return [frame_start]
    width = max(1, frame_end - frame_start)
    if sample_count == 1:
        return [frame_start + width // 2]
    samples: list[int] = []
    for index in range(sample_count):
        ratio = (index + 1) / (sample_count + 1)
        samples.append(frame_start + int(round((width - 1) * ratio)))
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


def _read_frame(media_path: str, frame_number: int):
    from facefusion.vision import read_static_image, read_video_frame

    suffix = Path(media_path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        return read_static_image(media_path)
    return read_video_frame(media_path, frame_number)


def _write_image(image_path: Path, frame) -> None:
    from facefusion.vision import write_image

    write_image(str(image_path), frame)


def _discover_project_references(
    facefusion_root: Path,
    project_id: str,
    sample_frames_per_shot: int,
    cluster_distance_threshold: float,
    source_hint_names: list[str] | None,
) -> dict[str, Any]:
    import numpy
    from facefusion.face_analyser import get_many_faces
    from facefusion.face_selector import calculate_face_distance, sort_faces_by_order

    project_dir = facefusion_root / ".multi-actor-projects" / project_id
    cast = _read_json(project_dir / "cast.json")
    shots = _read_json(project_dir / "shots.json")
    output_dir = project_dir / "manifests" / "reference-discovery"
    output_dir.mkdir(parents=True, exist_ok=True)
    clusters: list[dict[str, Any]] = []
    cluster_vectors: list[Any] = []
    samples: list[dict[str, Any]] = []
    per_shot_summary: list[dict[str, Any]] = []
    source_candidates = []
    existing_roles = cast.get("roles") or []
    for index, role in enumerate(existing_roles, start=1):
        face_path = (role.get("source_assets") or {}).get("face") or role.get("source_face_path")
        if face_path:
            source_candidates.append(
                {
                    "candidate_id": f"source-{index:02d}",
                    "role_id": role.get("role_id"),
                    "label": role.get("role_name") or role.get("role_id"),
                    "source_path": face_path,
                    "file_stem": Path(face_path).stem,
                }
            )
    for index, hint in enumerate(source_hint_names or [], start=1):
        source_candidates.append(
            {
                "candidate_id": f"hint-{index:02d}",
                "role_id": None,
                "label": hint,
                "source_path": None,
                "file_stem": _slugify(hint),
            }
        )

    for shot in shots.get("shots", []):
        target_path = shot["target_path"]
        suffix = Path(target_path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            sample_frames = [0]
        else:
            frame_total = _frame_count(target_path)
            if shot.get("frame_start") is not None or shot.get("frame_end") is not None:
                frame_start = int(shot.get("frame_start") or 0)
                frame_end = int(shot.get("frame_end") or frame_total)
            else:
                frame_start = 0
                frame_end = frame_total
            sample_frames = _sample_frames(frame_start, frame_end, sample_frames_per_shot)

        shot_cluster_ids: set[str] = set()
        for sample_index, frame_number in enumerate(sample_frames, start=1):
            frame = _read_frame(target_path, frame_number)
            if frame is None:
                continue
            faces = sort_faces_by_order(get_many_faces([frame]), "left-right")
            for face_index, face in enumerate(faces):
                embedding = face.embedding_norm if hasattr(face, "embedding_norm") else face.embedding
                assigned_cluster_index = None
                assigned_distance = None
                for cluster_index, cluster_embedding in enumerate(cluster_vectors):
                    distance = float(1 - numpy.dot(embedding, cluster_embedding))
                    if assigned_distance is None or distance < assigned_distance:
                        assigned_cluster_index = cluster_index
                        assigned_distance = distance
                if assigned_cluster_index is None or assigned_distance is None or assigned_distance > cluster_distance_threshold:
                    cluster_id = f"cluster-{len(clusters) + 1:02d}"
                    representative_path = output_dir / f"{shot['shot_id']}-{cluster_id}-rep.png"
                    crop = _crop_with_padding(frame, face.bounding_box)
                    if crop is not None:
                        _write_image(representative_path, crop)
                    clusters.append(
                        {
                            "cluster_id": cluster_id,
                            "label": f"Detected Face {len(clusters) + 1}",
                            "sample_count": 0,
                            "shot_ids": [],
                            "sample_paths": [str(representative_path)] if crop is not None else [],
                            "members": [],
                            "prefill_source_candidate": None,
                        }
                    )
                    cluster_vectors.append(embedding)
                    assigned_cluster_index = len(clusters) - 1
                    assigned_distance = 0.0
                cluster = clusters[assigned_cluster_index]
                cluster["sample_count"] += 1
                if shot["shot_id"] not in cluster["shot_ids"]:
                    cluster["shot_ids"].append(shot["shot_id"])
                crop = _crop_with_padding(frame, face.bounding_box)
                crop_path = output_dir / f"{shot['shot_id']}-{cluster['cluster_id']}-frame-{frame_number}-face-{face_index + 1}.png"
                if crop is not None:
                    _write_image(crop_path, crop)
                    if str(crop_path) not in cluster["sample_paths"]:
                        cluster["sample_paths"].append(str(crop_path))
                member = {
                    "shot_id": shot["shot_id"],
                    "target_path": target_path,
                    "frame_number": frame_number,
                    "face_index": face_index,
                    "bbox": [float(value) for value in face.bounding_box],
                    "distance_to_cluster": assigned_distance,
                    "crop_path": str(crop_path) if crop is not None else None,
                }
                cluster["members"].append(member)
                shot_cluster_ids.add(cluster["cluster_id"])
                samples.append(
                    {
                        "shot_id": shot["shot_id"],
                        "frame_number": frame_number,
                        "face_index": face_index,
                        "cluster_id": cluster["cluster_id"],
                        "crop_path": str(crop_path) if crop is not None else None,
                    }
                )
        per_shot_summary.append(
            {
                "shot_id": shot["shot_id"],
                "target_path": target_path,
                "detected_cluster_ids": sorted(shot_cluster_ids),
                "sample_frames": sample_frames,
            }
        )

    ordered_candidates = list(source_candidates)
    for index, cluster in enumerate(clusters):
        if index < len(ordered_candidates):
            cluster["prefill_source_candidate"] = ordered_candidates[index]
            cluster["suggested_role_name"] = ordered_candidates[index]["label"]
        else:
            cluster["suggested_role_name"] = cluster["label"]

    payload = {
        "project_id": project_id,
        "sample_frames_per_shot": sample_frames_per_shot,
        "cluster_distance_threshold": cluster_distance_threshold,
        "source_hint_names": source_hint_names or [],
        "source_candidates": ordered_candidates,
        "per_shot_summary": per_shot_summary,
        "clusters": clusters,
        "samples": samples,
        "suggested_groups": [
            {
                "group_id": f"group-{index + 1:02d}",
                "cluster_ids": [cluster["cluster_id"]],
                "suggested_role_id": _slugify(cluster.get("suggested_role_name") or cluster["cluster_id"]) or cluster["cluster_id"],
                "suggested_role_name": cluster.get("suggested_role_name") or cluster["cluster_id"],
                "prefill_source_candidate": cluster.get("prefill_source_candidate"),
            }
            for index, cluster in enumerate(clusters)
        ],
    }
    references_path = project_dir / "references.json"
    _write_json(references_path, payload)
    return {
        "project_id": project_id,
        "references_path": str(references_path),
        "cluster_count": len(clusters),
        "sample_count": len(samples),
        "references": payload,
    }


def main() -> int:
    args = parse_args()
    facefusion_root = Path(args.facefusion_root)
    if str(facefusion_root) not in sys.path:
        sys.path.insert(0, str(facefusion_root))
    _ensure_face_state()
    payload = _discover_project_references(
        facefusion_root=facefusion_root,
        project_id=args.project_id,
        sample_frames_per_shot=args.sample_frames_per_shot,
        cluster_distance_threshold=args.cluster_distance_threshold,
        source_hint_names=args.source_hint_names,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
