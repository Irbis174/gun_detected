from backend.db.models import TrackingUpdateModel
from backend.db.session import session_scope
from backend.domain.tracking_update import TrackingUpdate


def _to_domain(update: TrackingUpdateModel) -> TrackingUpdate:
    return TrackingUpdate(
        update_id=update.update_id,
        test_run_id=update.test_run_id,
        detection_id=update.detection_id,
        frame_index=update.frame_index,
        frame_ts=update.frame_ts,
        label=update.label,
        score=update.score,
        bbox=(
            update.bbox_x,
            update.bbox_y,
            update.bbox_w,
            update.bbox_h,
        ),
        track_id=update.track_id,
        received_at=update.received_at,
    )


class TrackingUpdateRepository:
    def add(self, update: TrackingUpdate) -> TrackingUpdate:
        x, y, width, height = update.bbox
        with session_scope() as session:
            model = TrackingUpdateModel(
                test_run_id=update.test_run_id,
                detection_id=update.detection_id,
                frame_index=update.frame_index,
                frame_ts=update.frame_ts,
                label=update.label,
                score=update.score,
                bbox_x=x,
                bbox_y=y,
                bbox_w=width,
                bbox_h=height,
                track_id=update.track_id,
                received_at=update.received_at,
            )
            session.add(model)
            session.flush()
            update.update_id = model.update_id
            return update

    def list_all(self) -> list[TrackingUpdate]:
        with session_scope() as session:
            models = (
                session.query(TrackingUpdateModel)
                .order_by(TrackingUpdateModel.update_id)
                .all()
            )
            return [_to_domain(model) for model in models]

    def list_by_test_run_id(self, test_run_id: int) -> list[TrackingUpdate]:
        with session_scope() as session:
            models = (
                session.query(TrackingUpdateModel)
                .filter(TrackingUpdateModel.test_run_id == test_run_id)
                .order_by(TrackingUpdateModel.update_id)
                .all()
            )
            return [_to_domain(model) for model in models]

    def latest(self) -> list[TrackingUpdate]:
        latest_by_detection: dict[int, TrackingUpdate] = {}
        for update in self.list_all():
            latest_by_detection[update.detection_id] = update
        return list(latest_by_detection.values())

    def latest_by_test_run_id(self, test_run_id: int) -> list[TrackingUpdate]:
        latest_by_detection: dict[int, TrackingUpdate] = {}
        for update in self.list_by_test_run_id(test_run_id):
            latest_by_detection[update.detection_id] = update
        return list(latest_by_detection.values())


tracking_update_repo = TrackingUpdateRepository()
