import datetime

import cv2

from backend.domain.time_detection import TemporaryDetection
from backend.repositories.input_source_repository import source_repo
from backend.repositories.test_run_repository import test_run_repo
from backend.services.candidate_tracker import CandidateTracker
from backend.services.ml_client import MLClientError, ml_client


class VideoTestRunner:
    def __init__(self, sample_every: int = 5):
        self.sample_every = sample_every
        self.tracker = CandidateTracker()

    async def run(self, test_run_id: int) -> None:
        test_run = test_run_repo.get(test_run_id)
        if test_run is None:
            raise ValueError(f'test_run_id={test_run_id} not found')

        source = source_repo.get(test_run.source_id)
        if source is None:
            raise ValueError(f'source_id={test_run.source_id} not found')

        if source.source_type != 'file':
            raise ValueError('VideoTestRunner currently supports only source_type=file')

        cap = cv2.VideoCapture(source.source)
        if not cap.isOpened():
            raise ValueError(f'Could not open video: {source.source}')

        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_index = 0

        test_run.status = 'running'
        test_run.started_at = datetime.datetime.now()
        test_run.finished_at = None

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                if frame_index % self.sample_every != 0:
                    frame_index += 1
                    continue

                ok, encoded = cv2.imencode('.jpg', frame)
                if not ok:
                    frame_index += 1
                    continue

                frame_bytes = encoded.tobytes()
                frame_ts = frame_index / fps if fps > 0 else float(frame_index)

                try:
                    ml_response = await ml_client.predict_image(
                        filename=f'frame_{frame_index:06d}.jpg',
                        content=frame_bytes,
                    )
                except MLClientError:
                    frame_index += 1
                    continue

                for detection in ml_response.detections:
                    temporary_detection = TemporaryDetection(
                        test_run_id=test_run_id,
                        source_id=source.source_id,
                        frame_index=frame_index,
                        frame_ts=frame_ts,
                        label=detection.label,
                        score=detection.score,
                        bbox=detection.bbox,
                        processing_ms=ml_response.processing_ms,
                    )
                    event = self.tracker.add(temporary_detection)
                    if event is not None:
                        test_run.detections_count += 1

                test_run.processed_frames += 1
                frame_index += 1
                self.tracker.prune_stale_candidates(test_run_id, frame_index)

            test_run.status = 'finished'
        except Exception:
            test_run.status = 'failed'
            raise
        finally:
            test_run.finished_at = datetime.datetime.now()
            cap.release()
