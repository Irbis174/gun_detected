from dataclasses import dataclass

@dataclass
class Items():
    id: int
    camera_id: int
    frame_ts: str
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]
    processing_ms: float