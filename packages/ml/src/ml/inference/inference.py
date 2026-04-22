from pathlib import Path
from time import perf_counter, sleep

import cv2
import httpx
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from ml.config import BACKEND_URL, ML_DEVICE
from ml.inference.yolo_model import get_model


router = APIRouter(prefix='/inference', tags=['inference'])

BBox = tuple[int, int, int, int]


class StreamRequest(BaseModel):
    source: str
    source_id: int
    detection_id: int
    test_run_id: int
    label: str
    bbox: BBox
    frame_index: int
    frame_ts: float


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
    missed_frames = 0

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

                results = model.predict(
                    source=frame,
                    verbose=False,
                    conf=0.25,
                    device=ML_DEVICE,
                )
                result = results[0]
                tracked_object = _select_tracked_object(
                    result=result,
                    expected_label=data.label,
                    previous_bbox=previous_bbox,
                )
                if tracked_object is None:
                    missed_frames += 1
                    current_frame_index += 1
                    _throttle_file_tracking(
                        is_file_source=is_file_source,
                        fps=fps,
                        started_at=started_at,
                        initial_frame_index=data.frame_index,
                        current_frame_index=current_frame_index,
                    )
                    continue

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


def _select_tracked_object(
    *,
    result,
    expected_label: str,
    previous_bbox: BBox,
) -> dict | None:
    boxes = getattr(result, 'boxes', None)
    if boxes is None or len(boxes) == 0:
        return None

    candidates: list[dict] = []
    for box in boxes:
        class_id = int(box.cls[0].item())
        label = result.names[class_id]
        if label != expected_label:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        candidates.append(
            {
                'label': label,
                'score': float(box.conf[0].item()),
                'bbox': (x1, y1, x2 - x1, y2 - y1),
                'track_id': None,
            }
        )

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda candidate: (
            _bbox_distance(candidate['bbox'], previous_bbox),
            -candidate['score'],
        ),
    )


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
