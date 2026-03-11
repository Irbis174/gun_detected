from dataclasses import dataclass

@dataclass
class DetectionEvent():
    detection_id: int
    test_run_id: int
    frame_ts: float
    label: str
    score: float
    bbox: tuple[int, int, int, int]
    processing_ms: float