import asyncio
from contextlib import suppress
from dataclasses import dataclass
import datetime
import logging
import os
from time import perf_counter
from typing import Any

import cv2

from backend.domain.detection_event import DetectionEvent
from backend.domain.test_run import TestRun
from backend.domain.time_detection import TemporaryDetection
from backend.domain.tracking_update import TrackingUpdate
from backend.repositories.detection_event_repository import detection_repo
from backend.repositories.input_source_repository import source_repo
from backend.repositories.preview_frame_repository import preview_frame_repo
from backend.repositories.test_run_repository import test_run_repo
from backend.repositories.tracking_update_repository import tracking_update_repo
from backend.services.candidate_tracker import CandidateTracker
from backend.services.detection_frame_store import detection_frame_store
from backend.services.ml_client import MLClientError, MLPredictImageResponse, ml_client

logger = logging.getLogger(__name__)

LIVE_PREVIEW_FPS_LIMIT = 30.0
LIVE_TARGET_LOCK_IOU_THRESHOLD = 0.10
LIVE_TARGET_LOCK_DISTANCE_MULTIPLIER = 1.5
LIVE_MAX_TARGET_MISSED_SECONDS = 5.0

BBox = tuple[int, int, int, int]


@dataclass(slots=True)
class PendingFrameInference:
    frame_index: int
    frame_ts: float
    frame: Any
    task: asyncio.Task[MLPredictImageResponse]


@dataclass(slots=True)
class LiveTrackingSession:
    detection_id: int
    label: str
    bbox: BBox
    track_id: int
    missed_frames: int
    max_missed_frames: int
    last_checked_frame: int


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
        tracking_started = False
        pending_live_inference: PendingFrameInference | None = None
        live_tracking: LiveTrackingSession | None = None
        normalized_source_type = source.source_type.strip().lower()
        is_live_source = normalized_source_type in {'webcam', 'camera'}
        next_preview_at = 0.0

        test_run.status = 'running'
        test_run.started_at = datetime.datetime.now()
        test_run.finished_at = None
        self._save_test_run(test_run)

        try:
            capture_source = self._resolve_capture_source(
                source_type=source.source_type,
                source_value=source.source,
            )
            cap = self._open_capture(
                source_type=normalized_source_type,
                capture_source=capture_source,
            )
            if not cap.isOpened():
                raise ValueError(
                    f'Could not open {source.source_type} source: {source.source}'
                )

            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            preview_interval = self._preview_interval_seconds(fps=fps)

            while True:
                if self._stop_requested:
                    test_run.status = 'stopped'
                    self._save_test_run(test_run)
                    break

                ok, frame = await self._read_frame(cap, live=is_live_source)
                if not ok:
                    if is_live_source:
                        raise RuntimeError(
                            f'Could not read frames from live source: {source.source}'
                        )
                    break

                now = perf_counter()
                if not is_live_source or now >= next_preview_at:
                    preview_bytes = await self._encode_preview_frame(
                        frame,
                        live=is_live_source,
                    )
                    if preview_bytes is not None:
                        preview_frame_repo.set(source.source_id, preview_bytes)
                    next_preview_at = now + preview_interval

                if is_live_source and pending_live_inference is not None:
                    if pending_live_inference.task.done():
                        inference = pending_live_inference
                        pending_live_inference = None
                        try:
                            ml_response = inference.task.result()
                        except MLClientError:
                            logger.exception(
                                'ML inference failed for live frame_index=%s',
                                inference.frame_index,
                            )
                        except Exception:
                            logger.exception(
                                'Unexpected ML inference error for live frame_index=%s',
                                inference.frame_index,
                            )
                        else:
                            if live_tracking is None:
                                event = self._handle_detections(
                                    test_run=test_run,
                                    source_id=source.source_id,
                                    source_value=source.source,
                                    frame=inference.frame,
                                    frame_index=inference.frame_index,
                                    frame_ts=inference.frame_ts,
                                    ml_response=ml_response,
                                    start_stream_tracking=False,
                                )
                                if event is not None:
                                    live_tracking = self._start_live_tracking(
                                        event=event,
                                        fps=fps,
                                    )
                            else:
                                live_tracking = self._handle_live_tracking_response(
                                    tracking=live_tracking,
                                    test_run_id=test_run.test_run_id,
                                    frame_index=inference.frame_index,
                                    frame_ts=inference.frame_ts,
                                    ml_response=ml_response,
                                )
                            test_run.processed_frames += 1
                            self._save_test_run(test_run)
                            if live_tracking is None:
                                self.tracker.prune_stale_candidates(
                                    test_run.test_run_id,
                                    inference.frame_index,
                                )

                if tracking_started and not is_live_source:
                    test_run.processed_frames += 1
                    self._save_test_run(test_run)
                    frame_index += 1
                    if normalized_source_type == 'file' and fps > 0:
                        await asyncio.sleep(max(0.0, 1.0 / fps))
                    continue

                should_run_inference = (
                    live_tracking is not None
                    or frame_index % self.sample_every == 0
                )
                if not should_run_inference:
                    frame_index += 1
                    if is_live_source:
                        await asyncio.sleep(0)
                    continue

                if is_live_source and pending_live_inference is not None:
                    frame_index += 1
                    await asyncio.sleep(0)
                    continue

                frame_bytes = await self._encode_inference_frame(
                    frame,
                    live=is_live_source,
                )
                if frame_bytes is None:
                    frame_index += 1
                    if is_live_source:
                        await asyncio.sleep(0)
                    continue

                frame_ts = self._compute_frame_ts(
                    frame_index=frame_index,
                    fps=fps,
                    started_monotonic=started_monotonic,
                )

                if is_live_source:
                    if pending_live_inference is None:
                        task = asyncio.create_task(
                            ml_client.predict_image(
                                filename=f'frame_{frame_index:06d}.jpg',
                                content=frame_bytes,
                            )
                        )
                        pending_live_inference = PendingFrameInference(
                            frame_index=frame_index,
                            frame_ts=frame_ts,
                            frame=frame.copy(),
                            task=task,
                        )

                    frame_index += 1
                    await asyncio.sleep(0)
                    continue

                try:
                    ml_response = await ml_client.predict_image(
                        filename=f'frame_{frame_index:06d}.jpg',
                        content=frame_bytes,
                    )
                except MLClientError:
                    frame_index += 1
                    continue

                event = self._handle_detections(
                    test_run=test_run,
                    source_id=source.source_id,
                    source_value=source.source,
                    frame=frame,
                    frame_index=frame_index,
                    frame_ts=frame_ts,
                    ml_response=ml_response,
                    start_stream_tracking=True,
                )
                tracking_started = event is not None
                test_run.processed_frames += 1
                self._save_test_run(test_run)
                frame_index += 1
                if not tracking_started:
                    self.tracker.prune_stale_candidates(test_run_id, frame_index)

            if test_run.status == 'running':
                test_run.status = 'finished'
        except Exception:
            test_run.status = 'failed'
            raise
        finally:
            if pending_live_inference is not None:
                pending_live_inference.task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await pending_live_inference.task
            test_run.finished_at = datetime.datetime.now()
            self._save_test_run(test_run)
            preview_frame_repo.clear(source.source_id)
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
    def _open_capture(
        *,
        source_type: str,
        capture_source: str | int,
    ) -> cv2.VideoCapture:
        if source_type not in {'webcam', 'camera'}:
            return cv2.VideoCapture(capture_source)

        backend_candidates: list[int | None] = []
        if os.name == 'nt':
            backend_candidates.append(getattr(cv2, 'CAP_DSHOW', None))
        backend_candidates.append(None)

        for backend in backend_candidates:
            if backend is None:
                cap = cv2.VideoCapture(capture_source)
            else:
                cap = cv2.VideoCapture(capture_source, backend)

            if not cap.isOpened():
                cap.release()
                continue

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        return cv2.VideoCapture(capture_source)

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

    @staticmethod
    def _preview_interval_seconds(*, fps: float) -> float:
        if fps > 0:
            return 1.0 / min(fps, LIVE_PREVIEW_FPS_LIMIT)
        return 1.0 / LIVE_PREVIEW_FPS_LIMIT

    @staticmethod
    async def _read_frame(
        cap: cv2.VideoCapture,
        *,
        live: bool,
    ):
        if live:
            return await asyncio.to_thread(cap.read)
        return cap.read()

    @staticmethod
    async def _encode_preview_frame(frame, *, live: bool) -> bytes | None:
        if live:
            return await asyncio.to_thread(
                VideoTestRunner._encode_frame,
                frame,
                70,
            )
        return VideoTestRunner._encode_frame(frame, 70)

    @staticmethod
    async def _encode_inference_frame(frame, *, live: bool) -> bytes | None:
        if live:
            return await asyncio.to_thread(
                VideoTestRunner._encode_frame,
                frame,
                85,
            )
        return VideoTestRunner._encode_frame(frame, 85)

    @staticmethod
    def _encode_frame(frame, jpeg_quality: int) -> bytes | None:
        ok, encoded = cv2.imencode(
            '.jpg',
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if not ok:
            return None
        return encoded.tobytes()

    def _schedule_tracking(
        self,
        *,
        source: str,
        source_id: int,
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
                source_id=source_id,
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

    def _handle_detections(
        self,
        *,
        test_run: TestRun,
        source_id: int,
        source_value: str,
        frame,
        frame_index: int,
        frame_ts: float,
        ml_response: MLPredictImageResponse,
        start_stream_tracking: bool,
    ) -> DetectionEvent | None:
        for detection in ml_response.detections:
            temporary_detection = TemporaryDetection(
                test_run_id=test_run.test_run_id,
                source_id=source_id,
                frame_index=frame_index,
                frame_ts=frame_ts,
                label=detection.label,
                score=detection.score,
                bbox=detection.bbox,
                processing_ms=ml_response.processing_ms,
            )
            event = self.tracker.add(temporary_detection)
            if event is None:
                continue

            event.frame_path = detection_frame_store.save(
                frame,
                test_run_id=test_run.test_run_id,
                detection_id=event.detection_id,
                frame_index=frame_index,
                bbox=event.bbox,
                label=event.label,
                score=event.score,
            )
            detection_repo.update_frame_path(
                event.detection_id,
                event.frame_path,
            )
            test_run.detections_count += 1
            self._save_test_run(test_run)
            self.tracker.reset(test_run.test_run_id)
            if start_stream_tracking:
                self._schedule_tracking(
                    source=source_value,
                    source_id=source_id,
                    test_run_id=test_run.test_run_id,
                    detection_id=event.detection_id,
                    frame_index=frame_index,
                    frame_ts=frame_ts,
                    bbox=event.bbox,
                    label=event.label,
                )
            return event

        return None

    def _start_live_tracking(
        self,
        *,
        event: DetectionEvent,
        fps: float,
    ) -> LiveTrackingSession:
        frame_index = event.frame_index or 0
        track_id = event.detection_id
        tracking = LiveTrackingSession(
            detection_id=event.detection_id,
            label=event.label,
            bbox=event.bbox,
            track_id=track_id,
            missed_frames=0,
            max_missed_frames=self._max_live_missed_frames(fps=fps),
            last_checked_frame=frame_index,
        )
        self._add_tracking_update(
            test_run_id=event.test_run_id,
            detection_id=event.detection_id,
            frame_index=frame_index,
            frame_ts=event.frame_ts,
            label=event.label,
            score=event.score,
            bbox=event.bbox,
            track_id=track_id,
        )
        return tracking

    def _handle_live_tracking_response(
        self,
        *,
        tracking: LiveTrackingSession,
        test_run_id: int,
        frame_index: int,
        frame_ts: float,
        ml_response: MLPredictImageResponse,
    ) -> LiveTrackingSession | None:
        frames_since_last_check = max(1, frame_index - tracking.last_checked_frame)
        tracking.last_checked_frame = frame_index

        detection = self._select_live_tracking_detection(
            tracking=tracking,
            ml_response=ml_response,
        )
        if detection is None:
            tracking.missed_frames += frames_since_last_check
            if tracking.missed_frames > tracking.max_missed_frames:
                return None
            return tracking

        tracking.missed_frames = 0
        tracking.bbox = detection.bbox
        self._add_tracking_update(
            test_run_id=test_run_id,
            detection_id=tracking.detection_id,
            frame_index=frame_index,
            frame_ts=frame_ts,
            label=detection.label,
            score=detection.score,
            bbox=detection.bbox,
            track_id=tracking.track_id,
        )
        return tracking

    def _select_live_tracking_detection(
        self,
        *,
        tracking: LiveTrackingSession,
        ml_response: MLPredictImageResponse,
    ):
        related_detections = [
            detection
            for detection in ml_response.detections
            if detection.label == tracking.label
            and self._is_related_bbox(detection.bbox, tracking.bbox)
        ]
        if not related_detections:
            return None

        return max(
            related_detections,
            key=lambda detection: (
                self._bbox_iou(detection.bbox, tracking.bbox),
                detection.score,
                -self._bbox_distance(detection.bbox, tracking.bbox),
            ),
        )

    @staticmethod
    def _add_tracking_update(
        *,
        test_run_id: int,
        detection_id: int,
        frame_index: int,
        frame_ts: float,
        label: str,
        score: float,
        bbox: BBox,
        track_id: int | None,
    ) -> None:
        tracking_update_repo.add(
            TrackingUpdate(
                update_id=0,
                test_run_id=test_run_id,
                detection_id=detection_id,
                frame_index=frame_index,
                frame_ts=frame_ts,
                label=label,
                score=score,
                bbox=bbox,
                track_id=track_id,
                received_at=datetime.datetime.now(),
            )
        )

    @staticmethod
    def _max_live_missed_frames(*, fps: float) -> int:
        frame_rate = fps if fps > 0 else 30.0
        return max(30, int(round(frame_rate * LIVE_MAX_TARGET_MISSED_SECONDS)))

    @staticmethod
    def _is_related_bbox(bbox1: BBox, bbox2: BBox) -> bool:
        if VideoTestRunner._bbox_iou(bbox1, bbox2) >= LIVE_TARGET_LOCK_IOU_THRESHOLD:
            return True

        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        distance_threshold = (
            max(1.0, float(max(w1, h1)), float(max(w2, h2)))
            * LIVE_TARGET_LOCK_DISTANCE_MULTIPLIER
        )
        return (
            VideoTestRunner._bbox_distance((x1, y1, w1, h1), (x2, y2, w2, h2))
            <= distance_threshold
        )

    @staticmethod
    def _bbox_iou(bbox1: BBox, bbox2: BBox) -> float:
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)

        intersection_width = max(0, right - left)
        intersection_height = max(0, bottom - top)
        intersection_area = intersection_width * intersection_height
        if intersection_area <= 0:
            return 0.0

        area1 = max(0, w1) * max(0, h1)
        area2 = max(0, w2) * max(0, h2)
        union_area = area1 + area2 - intersection_area
        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    @staticmethod
    def _bbox_distance(bbox1: BBox, bbox2: BBox) -> float:
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        center_1 = (x1 + w1 / 2.0, y1 + h1 / 2.0)
        center_2 = (x2 + w2 / 2.0, y2 + h2 / 2.0)
        dx = center_1[0] - center_2[0]
        dy = center_1[1] - center_2[1]
        return (dx * dx + dy * dy) ** 0.5

    async def _start_tracking(
        self,
        *,
        source: str,
        source_id: int,
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
                source_id=source_id,
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

    @staticmethod
    def _save_test_run(test_run: TestRun) -> None:
        try:
            test_run_repo.update(test_run)
        except Exception:
            logger.exception(
                'Could not persist test_run_id=%s state',
                test_run.test_run_id,
            )
