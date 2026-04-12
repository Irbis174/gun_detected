from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from config import BACKEND_URL
from ml.inference.yolo_model import get_model
import requests
import httpx
from time import perf_counter, time

router = APIRouter(prefix='/inference', tags=['inference'])

BBox = tuple[int, int, int, int]


class StreamRequest(BaseModel):
    source: str
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

    results = model.track(
        source=_resolve_tracking_source(data.source),
        tracker='bytetrack.yaml',
        persist=True,
        stream=True,
        verbose=False,
    )

    with httpx.Client(timeout=5.0) as client:
        current_frame_index = data.frame_index
        started_at = perf_counter()
        for result in results:
            current_frame_ts = data.frame_ts + (perf_counter() - started_at)
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy.tolist())
                bbox = [x1, y1, x2 - x1, y2 - y1]
                score = float(box.conf[0].item())
                class_id = int(box.cls[0].item())
                label = result.names[class_id]
                track_id = None
                if box.id is not None:
                    track_id = int(box.id[0].item())
                payload = {
                    "test_run_id": data.test_run_id,
                    "detection_id": data.detection_id,
                    "frame_index": current_frame_index,
                    "frame_ts": current_frame_ts,
                    "label": label,
                    "score": score,
                    "bbox": bbox,
                    "track_id": track_id,
                }

                client.post(
                    f"{BACKEND_URL}/tracking-updates",
                    json=payload,
                ).raise_for_status()
            current_frame_index += 1

def _resolve_tracking_source(source: str) -> str | int:
    stripped_source = source.strip()
    if stripped_source.isdecimal():
        return int(stripped_source)
    return source
