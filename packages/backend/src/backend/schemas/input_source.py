from pydantic import BaseModel

class InputSourceCreate(BaseModel):
    name: str
    source_type: str
    source: str


class InputSourceRead(BaseModel):
    source_id: int
    name: str
    source_type: str
    source: str
    connected: bool