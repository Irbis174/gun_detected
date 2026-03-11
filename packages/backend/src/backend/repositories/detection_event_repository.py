from backend.domain.detection_event import DetectionEvent

class InMemoryDetectionRepo():
    def __init__(self):
        self._items: list[DetectionEvent] = []
        self._next_id: int = 1

    def add(self, detection: DetectionEvent):
        detection.detection_id = self._next_id
        self._items.append(detection)
        self._next_id += 1

    def list_all(self) -> list[DetectionEvent]:
        return self._items.copy()

    def get(self, id: int):
        for i in range(len(self._items)):
            if self._items[i].detection_id == id:
                return self._items[i]
        return None

    def list_by_test_run_id(self, id: int):
        all_detect = []
        for i in range(len(self._items)):
            if self._items[i].test_run_id == id:
                all_detect.append(self._items[i])
        return all_detect

    
detection_repo = InMemoryDetectionRepo()