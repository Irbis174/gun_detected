from backend.db.models import TestRunModel
from backend.db.session import session_scope
from backend.domain.test_run import TestRun


def _to_domain(test_run: TestRunModel) -> TestRun:
    return TestRun(
        test_run_id=test_run.test_run_id,
        source_id=test_run.source_id,
        status=test_run.status,
        started_at=test_run.started_at,
        finished_at=test_run.finished_at,
        processed_frames=test_run.processed_frames,
        detections_count=test_run.detections_count,
    )


class TestRunRepository:
    def add(self, test_run: TestRun) -> TestRun:
        with session_scope() as session:
            model = TestRunModel(
                source_id=test_run.source_id,
                status=test_run.status,
                started_at=test_run.started_at,
                finished_at=test_run.finished_at,
                processed_frames=test_run.processed_frames,
                detections_count=test_run.detections_count,
            )
            session.add(model)
            session.flush()
            test_run.test_run_id = model.test_run_id
            return test_run

    def list(self) -> list[TestRun]:
        with session_scope() as session:
            models = (
                session.query(TestRunModel)
                .order_by(TestRunModel.test_run_id.desc())
                .all()
            )
            return [_to_domain(model) for model in models]

    def get(self, id: int) -> TestRun | None:
        with session_scope() as session:
            model = session.get(TestRunModel, id)
            if model is None:
                return None
            return _to_domain(model)

    def update(self, test_run: TestRun) -> TestRun:
        with session_scope() as session:
            model = session.get(TestRunModel, test_run.test_run_id)
            if model is None:
                raise ValueError(f'test_run_id={test_run.test_run_id} not found')

            model.status = test_run.status
            model.started_at = test_run.started_at
            model.finished_at = test_run.finished_at
            model.processed_frames = test_run.processed_frames
            model.detections_count = test_run.detections_count
            session.flush()
            return test_run


test_run_repo = TestRunRepository()
