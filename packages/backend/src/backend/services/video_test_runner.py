import asyncio
import datetime
import logging
from time import perf_counter

import cv2

from backend.domain.time_detection import TemporaryDetection
from backend.repositories.input_source_repository import source_repo
from backend.repositories.test_run_repository import test_run_repo
from backend.services.candidate_tracker import CandidateTracker
from backend.services.ml_client import MLClientError, ml_client

logger = logging.getLogger(__name__)


class VideoTestRunner:
    def __init__(self, sample_every: int = 5):
        self.sample_every = sample_every
        self.tracker = CandidateTracker()
        self._tracking_tasks: set[asyncio.Task[None]] = set()
        self._stop_requested = False

    async def run(self, test_run_id: int) -> None:
        test_run = test_run_repo.get(test_run_id)
        if test_run is None:
            raise ValueError(f'test_run_id={test_run_id} not found')

        source = source_repo.get(test_run.source_id)
        if source is None:
            raise ValueError(f'source_id={test_run.source_id} not found')

        cap: cv2.VideoCapture | None = None
        frame_index = 0
        fps = 0.0
        started_monotonic = perf_counter()

        test_run.status = 'running'
        test_run.started_at = datetime.datetime.now()
        test_run.finished_at = None

        try:
            capture_source = self._resolve_capture_source(
                source_type=source.source_type,
                source_value=source.source,
            )
            cap = cv2.VideoCapture(capture_source)
            if not cap.isOpened():
                raise ValueError(
                    f'Could not open {source.source_type} source: {source.source}'
                )

            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0

            while True:
                if self._stop_requested:
                    test_run.status = 'stopped'
                    break

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
                frame_ts = self._compute_frame_ts(
                    frame_index=frame_index,
                    fps=fps,
                    started_monotonic=started_monotonic,
                )

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
                        self._schedule_tracking(
                            source=source.source,
                            test_run_id=test_run_id,
                            detection_id=event.detection_id,
                            frame_index=frame_index,
                            frame_ts=frame_ts,
                            bbox=event.bbox,
                            label=event.label,
                        )
                test_run.processed_frames += 1
                frame_index += 1
                self.tracker.prune_stale_candidates(test_run_id, frame_index)

            test_run.status = 'finished'
        except Exception:
            test_run.status = 'failed'
            raise
        finally:
            test_run.finished_at = datetime.datetime.now()
            if cap is not None:
                cap.release()

    @staticmethod
    def _resolve_capture_source(*, source_type: str, source_value: str) -> str | int:
        normalized_type = source_type.strip().lower()
        if normalized_type == 'file':
            return source_value

        if normalized_type in {'webcam', 'camera'}:
            stripped_source = source_value.strip()
            if not stripped_source:
                return 0

            try:
                return int(stripped_source)
            except ValueError:
                return source_value

        raise ValueError(
            'VideoTestRunner currently supports source_type=file and source_type=webcam'
        )

    @staticmethod
    def _compute_frame_ts(
        *,
        frame_index: int,
        fps: float,
        started_monotonic: float,
    ) -> float:
        if fps > 0:
            return frame_index / fps
        return max(0.0, perf_counter() - started_monotonic)

    def _schedule_tracking(
        self,
        *,
        source: str,
        test_run_id: int,
        detection_id: int,
        frame_index: int,
        frame_ts: float,
        bbox: tuple[int, int, int, int],
        label: str,
    ) -> None:
        task = asyncio.create_task(
            self._start_tracking(
                source=source,
                test_run_id=test_run_id,
                detection_id=detection_id,
                frame_index=frame_index,
                frame_ts=frame_ts,
                bbox=bbox,
                label=label,
            )
        )
        self._tracking_tasks.add(task)
        task.add_done_callback(self._tracking_tasks.discard)

    async def _start_tracking(
        self,
        *,
        source: str,
        test_run_id: int,
        detection_id: int,
        frame_index: int,
        frame_ts: float,
        bbox: tuple[int, int, int, int],
        label: str,
    ) -> None:
        try:
            await ml_client.run_tracking(
                source=source,
                test_run_id=test_run_id,
                detection_id=detection_id,
                frame_index=frame_index,
                frame_ts=frame_ts,
                bbox=bbox,
                label=label,
            )
        except MLClientError as error:
            logger.warning(
                'Could not start stream tracking for detection_id=%s: %s',
                detection_id,
                error,
            )
        except Exception:
            logger.exception(
                'Unexpected error while starting stream tracking for detection_id=%s',
                detection_id,
            )
    def request_stop(self) -> None:
        self._stop_requested = True
