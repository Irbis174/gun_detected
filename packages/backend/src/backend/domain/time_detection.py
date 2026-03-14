from dataclasses import dataclass
import datetime


@dataclass
class TemporaryDetection:
    test_run_id: int
    source_id: int
    label: str
    bbox: tuple(int, int, int, int)
    first_seen_frame: datetime.datetime
    last_seen_frame: datetime.datetime
    hits: int
    confirmed: bool
