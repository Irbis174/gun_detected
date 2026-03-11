from dataclasses import dataclass

@dataclass
class InputSource:
    source_id: int
    name: str
    source_type: str
    source: str
    connected: bool