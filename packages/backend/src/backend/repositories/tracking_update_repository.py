from backend.domain.tracking_update import TrackingUpdate


class TrackingUpdateRepository:
    def __init__(self):
        self._items: list[TrackingUpdate] = []
        self._next_id = 1

    def add(self, update: TrackingUpdate) -> TrackingUpdate:
        update.update_id = self._next_id
        self._items.append(update)
        self._next_id += 1
        return update

    def list_all(self) -> list[TrackingUpdate]:
        return self._items.copy()

    def list_by_test_run_id(self, test_run_id: int) -> list[TrackingUpdate]:
        return [
            update for update in self._items
            if update.test_run_id == test_run_id
        ]

    def latest(self) -> list[TrackingUpdate]:
        latest_by_detection: dict[int, TrackingUpdate] = {}
        for update in self._items:
            latest_by_detection[update.detection_id] = update
        return list(latest_by_detection.values())


tracking_update_repo = TrackingUpdateRepository()
