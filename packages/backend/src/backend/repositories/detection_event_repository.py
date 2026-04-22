from backend.db.models import DetectionModel
from backend.db.session import session_scope
from backend.domain.detection_event import DetectionEvent


def _to_domain(detection: DetectionModel) -> DetectionEvent:
    return DetectionEvent(
        detection_id=detection.detection_id,
        test_run_id=detection.test_run_id,
        frame_ts=detection.frame_ts,
        label=detection.label,
        score=detection.score,
        bbox=(
            detection.bbox_x,
            detection.bbox_y,
            detection.bbox_w,
            detection.bbox_h,
        ),
        processing_ms=detection.processing_ms,
        source_id=detection.source_id,
        frame_index=detection.frame_index,
        frame_path=detection.frame_path,
    )


class DetectionRepository:
    def add(self, detection: DetectionEvent) -> DetectionEvent:
        x, y, width, height = detection.bbox
        with session_scope() as session:
            model = DetectionModel(
                test_run_id=detection.test_run_id,
                source_id=detection.source_id,
                frame_index=detection.frame_index,
                frame_ts=detection.frame_ts,
                label=detection.label,
                score=detection.score,
                bbox_x=x,
                bbox_y=y,
                bbox_w=width,
                bbox_h=height,
                processing_ms=detection.processing_ms,
                frame_path=detection.frame_path,
            )
            session.add(model)
            session.flush()
            detection.detection_id = model.detection_id
            return detection

    def list_all(self) -> list[DetectionEvent]:
        with session_scope() as session:
            models = (
                session.query(DetectionModel)
                .order_by(DetectionModel.detection_id)
                .all()
            )
            return [_to_domain(model) for model in models]

    def get(self, id: int) -> DetectionEvent | None:
        with session_scope() as session:
            model = session.get(DetectionModel, id)
            if model is None:
                return None
            return _to_domain(model)

    def list_by_test_run_id(self, id: int) -> list[DetectionEvent]:
        with session_scope() as session:
            models = (
                session.query(DetectionModel)
                .filter(DetectionModel.test_run_id == id)
                .order_by(DetectionModel.detection_id)
                .all()
            )
            return [_to_domain(model) for model in models]

    def update_frame_path(
        self,
        detection_id: int,
        frame_path: str | None,
    ) -> DetectionEvent | None:
        with session_scope() as session:
            model = session.get(DetectionModel, detection_id)
            if model is None:
                return None

            model.frame_path = frame_path
            session.flush()
            return _to_domain(model)


detection_repo = DetectionRepository()
