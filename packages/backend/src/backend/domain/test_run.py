from dataclasses import dataclass
import datetime 

@dataclass
class TestRun:
    test_id: int
    source_id: int
    status: str
    started_at: datetime.datetime
    finished_at: datetime.datetime
    processed_frames: int
    detections_count: int