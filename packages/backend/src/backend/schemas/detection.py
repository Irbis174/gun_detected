from pydantic import BaseModel, ConfigDict, Field


type BBox = tuple[int, int, int, int]


class DetectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detection_id: int
    test_run_id: int
    source_id: int | None = None
    frame_index: int | None = None
    frame_ts: float = Field(ge=0.0)
    label: str
    score: float = Field(ge=0.0, le=1.0)
    bbox: BBox = Field(
        description='Bounding box in pixels as (x, y, w, h).',
    )
    processing_ms: float = Field(ge=0.0)
    frame_path: str | None = Field(
        default=None,
        description='Saved detection frame image path.',
    )
