from dataclasses import dataclass
import datetime


BBox = tuple[int, int, int, int]


@dataclass
class TrackingUpdate:
    update_id: int
    test_run_id: int
    detection_id: int
    frame_index: int
    frame_ts: float
    label: str
    score: float
    bbox: BBox
    track_id: int | None
    received_at: datetime.datetime
