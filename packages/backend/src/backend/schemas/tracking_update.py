import datetime

from pydantic import BaseModel, Field

BBox = tuple[int, int, int, int]


class TrackingUpdateCreate(BaseModel):
    test_run_id: int
    detection_id: int
    frame_index: int
    frame_ts: float = Field(ge=0.0)
    label: str
    score: float = Field(ge=0.0, le=1.0)
    bbox: BBox
    track_id: int | None = None


class TrackingUpdateRead(TrackingUpdateCreate):
    update_id: int
    received_at: datetime.datetime
