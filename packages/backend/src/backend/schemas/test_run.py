from pydantic import BaseModel
import datetime

class TestRunCreate(BaseModel):
    source_id: int

class TestRunRead(BaseModel):
    test_run_id: int
    source_id: int
    status: str
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    processed_frames: int
    detections_count: int