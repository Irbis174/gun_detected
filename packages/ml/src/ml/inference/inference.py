from pathlib import Path
from time import perf_counter, sleep
from typing import TypedDict

import cv2
import httpx
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import IterableSimpleNamespace, YAML

from ml.config import BACKEND_URL, ML_DEVICE, TRACKER_CONFIG_PATH
from ml.inference.yolo_model import get_model


router = APIRouter(prefix='/inference', tags=['inference'])

BBox = tuple[int, int, int, int]
TARGET_LOCK_IOU_THRESHOLD = 0.10
TARGET_LOCK_DISTANCE_MULTIPLIER = 1.5
MAX_TARGET_MISSED_SECONDS = 5.0


class StreamRequest(BaseModel):
    source: str
    source_id: int
    detection_id: int
    test_run_id: int
    label: str
    bbox: BBox
    frame_index: int
    frame_ts: float


class TrackCandidate(TypedDict):
    label: str
    score: float
    bbox: BBox
    track_id: int


@router.post('/stream')
async def stream(
    data: StreamRequest,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(run_stream_tracking, data)
    return {'status': 'started'}


def run_stream_tracking(data: StreamRequest) -> None:
    model = get_model()
    capture_source = _resolve_tracking_source(data.source)
    capture = cv2.VideoCapture(capture_source)
    if not capture.isOpened():
        return

    is_file_source = _is_file_source(data.source)
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    if is_file_source and data.frame_index > 0:
        capture.set(cv2.CAP_PROP_POS_FRAMES, data.frame_index)

    current_frame_index = data.frame_index
    started_at = perf_counter()
    previous_bbox = data.bbox
    target_track_id: int | None = None
    missed_frames = 0
    tracker, tracking_conf = _create_byte_tracker(fps=fps)
    max_missed_frames = _max_missed_frames(fps=fps)

    try:
        with httpx.Client(timeout=5.0) as client:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                preview_bytes = _encode_preview_frame(frame)
                if preview_bytes is not None:
                    try:
                        client.post(
                            f'{BACKEND_URL}/sources/{data.source_id}/preview',
                            content=preview_bytes,
                            headers={'content-type': 'image/jpeg'},
                        ).raise_for_status()
                    except httpx.HTTPError:
                        pass

                current_frame_ts = _compute_frame_ts(
                    frame_index=current_frame_index,
                    fps=fps,
                    initial_frame_ts=data.frame_ts,
                    started_at=started_at,
                )

                track_candidates = _track_frame(
                    model=model,
                    tracker=tracker,
                    frame=frame,
                    conf=tracking_conf,
                    expected_label=data.label,
                )
                tracked_object = _select_tracked_object(
                    candidates=track_candidates,
                    target_track_id=target_track_id,
                    previous_bbox=previous_bbox,
                )
                if tracked_object is None:
                    missed_frames += 1
                    if (
                        target_track_id is not None
                        and missed_frames > max_missed_frames
                    ):
                        break
                    current_frame_index += 1
                    _throttle_file_tracking(
                        is_file_source=is_file_source,
                        fps=fps,
                        started_at=started_at,
                        initial_frame_index=data.frame_index,
                        current_frame_index=current_frame_index,
                    )
                    continue

                if target_track_id is None:
                    target_track_id = tracked_object['track_id']

                missed_frames = 0
                previous_bbox = tracked_object['bbox']

                payload = {
                    'test_run_id': data.test_run_id,
                    'detection_id': data.detection_id,
                    'frame_index': current_frame_index,
                    'frame_ts': current_frame_ts,
                    'label': tracked_object['label'],
                    'score': tracked_object['score'],
                    'bbox': list(tracked_object['bbox']),
                    'track_id': tracked_object['track_id'],
                }

                try:
                    client.post(
                        f'{BACKEND_URL}/tracking-updates',
                        json=payload,
                    ).raise_for_status()
                except httpx.HTTPError:
                    pass

                current_frame_index += 1
                _throttle_file_tracking(
                    is_file_source=is_file_source,
                    fps=fps,
                    started_at=started_at,
                    initial_frame_index=data.frame_index,
                    current_frame_index=current_frame_index,
                )
    finally:
        capture.release()


def _resolve_tracking_source(source: str) -> str | int:
    stripped_source = source.strip()
    if stripped_source.isdecimal():
        return int(stripped_source)
    return source


def _is_file_source(source: str) -> bool:
    stripped_source = source.strip()
    if stripped_source.isdecimal():
        return False
    if stripped_source.lower().startswith(('rtsp://', 'http://', 'https://')):
        return False
    return Path(stripped_source).suffix != ''


def _create_byte_tracker(*, fps: float) -> tuple[BYTETracker, float]:
    cfg = IterableSimpleNamespace(**YAML.load(str(TRACKER_CONFIG_PATH)))
    frame_rate = int(round(fps)) if fps > 0 else 30
    tracker = BYTETracker(args=cfg, frame_rate=max(1, frame_rate))
    return tracker, float(cfg.track_low_thresh)


def _max_missed_frames(*, fps: float) -> int:
    frame_rate = fps if fps > 0 else 30.0
    return max(30, int(round(frame_rate * MAX_TARGET_MISSED_SECONDS)))


def _compute_frame_ts(
    *,
    frame_index: int,
    fps: float,
    initial_frame_ts: float,
    started_at: float,
) -> float:
    if fps > 0:
        return frame_index / fps
    return initial_frame_ts + max(0.0, perf_counter() - started_at)


def _track_frame(
    *,
    model,
    tracker: BYTETracker,
    frame,
    conf: float,
    expected_label: str,
) -> list[TrackCandidate]:
    results = model.predict(
        source=frame,
        verbose=False,
        conf=conf,
        device=ML_DEVICE,
    )
    result = results[0]
    boxes = getattr(result, 'boxes', None)
    if boxes is None:
        return []

    tracks = tracker.update(boxes.cpu().numpy(), result.orig_img)
    if len(tracks) == 0:
        return []

    candidates: list[TrackCandidate] = []
    for track in tracks:
        if len(track) < 7:
            continue

        x1, y1, x2, y2 = map(int, track[:4].tolist())
        class_id = int(track[6])
        label = result.names[class_id]
        if label != expected_label:
            continue

        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            continue

        candidates.append(
            {
                'label': label,
                'score': float(track[5]),
                'bbox': (x1, y1, width, height),
                'track_id': int(track[4]),
            }
        )

    return candidates


def _select_tracked_object(
    *,
    candidates: list[TrackCandidate],
    target_track_id: int | None,
    previous_bbox: BBox,
) -> TrackCandidate | None:
    if not candidates:
        return None

    if target_track_id is not None:
        for candidate in candidates:
            if candidate['track_id'] == target_track_id:
                return candidate
        return None

    related_candidates = [
        candidate
        for candidate in candidates
        if _is_related_bbox(candidate['bbox'], previous_bbox)
    ]
    if not related_candidates:
        return None

    return max(
        related_candidates,
        key=lambda candidate: (
            _bbox_iou(candidate['bbox'], previous_bbox),
            candidate['score'],
            -_bbox_distance(candidate['bbox'], previous_bbox),
        ),
    )


def _is_related_bbox(bbox1: BBox, bbox2: BBox) -> bool:
    if _bbox_iou(bbox1, bbox2) >= TARGET_LOCK_IOU_THRESHOLD:
        return True

    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    distance_threshold = (
        max(1.0, float(max(w1, h1)), float(max(w2, h2)))
        * TARGET_LOCK_DISTANCE_MULTIPLIER
    )
    return _bbox_distance((x1, y1, w1, h1), (x2, y2, w2, h2)) <= distance_threshold


def _bbox_iou(bbox1: BBox, bbox2: BBox) -> float:
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    left = max(x1, x2)
    top = max(y1, y2)
    right = min(x1 + w1, x2 + w2)
    bottom = min(y1 + h1, y2 + h2)

    intersection_width = max(0, right - left)
    intersection_height = max(0, bottom - top)
    intersection_area = intersection_width * intersection_height
    if intersection_area <= 0:
        return 0.0

    area1 = max(0, w1) * max(0, h1)
    area2 = max(0, w2) * max(0, h2)
    union_area = area1 + area2 - intersection_area
    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def _bbox_distance(bbox1: BBox, bbox2: BBox) -> float:
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    center_1 = (x1 + w1 / 2.0, y1 + h1 / 2.0)
    center_2 = (x2 + w2 / 2.0, y2 + h2 / 2.0)
    dx = center_1[0] - center_2[0]
    dy = center_1[1] - center_2[1]
    return (dx * dx + dy * dy) ** 0.5


def _throttle_file_tracking(
    *,
    is_file_source: bool,
    fps: float,
    started_at: float,
    initial_frame_index: int,
    current_frame_index: int,
) -> None:
    if not is_file_source or fps <= 0:
        return

    elapsed = perf_counter() - started_at
    expected_elapsed = max(0.0, (current_frame_index - initial_frame_index) / fps)
    remaining = expected_elapsed - elapsed
    if remaining > 0:
        sleep(min(remaining, 0.1))


def _encode_preview_frame(frame) -> bytes | None:
    ok, encoded = cv2.imencode(
        '.jpg',
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 70],
    )
    if not ok:
        return None
    return encoded.tobytes()
