from fastapi import  APIRouter, Field
from pydantic import BaseModel
from backend.config import ML_URL


class DetectionRead(BaseModel):
    id: int
    camera_id: int
    frame_ts: str
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[int, int, int, int]
    processing_ms: float = Field(ge=0.0)