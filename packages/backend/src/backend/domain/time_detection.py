from dataclasses import dataclass


type BBox = tuple[int, int, int, int]


@dataclass(slots=True)
class TemporaryDetection:
    test_run_id: int
    source_id: int
    frame_index: int
    frame_ts: float
    label: str
    score: float
    bbox: BBox
    processing_ms: float


@dataclass(slots=True)
class DetectionCandidate:
    test_run_id: int
    source_id: int
    label: str
    bbox: BBox
    first_seen_frame: int
    last_seen_frame: int
    first_seen_ts: float
    last_seen_ts: float
    hits: int
    best_score: float
    last_processing_ms: float
    confirmed: bool = False
