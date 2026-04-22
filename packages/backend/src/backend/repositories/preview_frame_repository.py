class PreviewFrameRepository:
    def __init__(self):
        self._frames: dict[int, bytes] = {}

    def set(self, source_id: int, frame_bytes: bytes) -> None:
        self._frames[source_id] = frame_bytes

    def get(self, source_id: int) -> bytes | None:
        return self._frames.get(source_id)

    def clear(self, source_id: int) -> None:
        self._frames.pop(source_id, None)


preview_frame_repo = PreviewFrameRepository()
