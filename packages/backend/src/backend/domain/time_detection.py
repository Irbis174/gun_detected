from dataclasses import dataclass


@dataclass
class TemporaryDetection:
    test_run_id: int
    source_id: int
    bbox: tuple[int, int, int, int]
    frame_index: int

@dataclass
class DetectionCandidate:
    test_run_id: int
    source_id: int
    bbox: tuple[int, int, int, int]
    first_seen_frame: int
    last_seen_frame: int
    hits: int
    confirmed: bool
