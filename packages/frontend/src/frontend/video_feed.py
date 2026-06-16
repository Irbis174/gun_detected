from __future__ import annotations

import os
import time

import cv2
import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from frontend.config import BACKEND_URL


class VideoFeedThread(QThread):
    frame_ready = Signal(QImage)
    connection_changed = Signal(bool)
    error = Signal(str)

    def __init__(self, *, source_type: str, source: str, parent=None):
        super().__init__(parent)
        self.source_type = source_type
        self.source = source

    def run(self) -> None:
        capture_source = self._resolve_source(
            source_type=self.source_type,
            source_value=self.source,
        )
        cap = _open_capture(
            source_type=self.source_type,
            capture_source=capture_source,
        )
        if not cap.isOpened():
            self.connection_changed.emit(False)
            self.error.emit(f'Не удалось открыть источник: {self.source}')
            return

        self.connection_changed.emit(True)
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_delay_ms = max(15, int(1000 / fps)) if fps > 0 else 33

        try:
            while not self.isInterruptionRequested():
                ok, frame = cap.read()
                if not ok:
                    if self.source_type.strip().lower() == 'file':
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    self.error.emit(
                        f'Не удалось получить кадры из источника: {self.source}'
                    )
                    break

                image = _convert_cv_frame_to_qimage(frame)
                self.frame_ready.emit(image)
                self.msleep(frame_delay_ms)
        finally:
            cap.release()
            self.connection_changed.emit(False)

    def stop(self) -> None:
        self.requestInterruption()
        if self.isRunning():
            self.wait()

    @staticmethod
    def _resolve_source(*, source_type: str, source_value: str) -> str | int:
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

        return source_value


class BackendPreviewThread(QThread):
    frame_ready = Signal(QImage)
    connection_changed = Signal(bool)
    error = Signal(str)

    def __init__(
        self,
        *,
        source_id: int,
        base_url: str = BACKEND_URL,
        poll_interval_seconds: float = 0.04,
        parent=None,
    ):
        super().__init__(parent)
        self.source_id = source_id
        self.base_url = base_url.rstrip('/')
        self.poll_interval_seconds = poll_interval_seconds

    def run(self) -> None:
        session = requests.Session()
        was_connected = False
        preview_url = f'{self.base_url}/sources/{self.source_id}/preview'

        try:
            while not self.isInterruptionRequested():
                try:
                    response = session.get(preview_url, timeout=2.0)
                except requests.RequestException as error:
                    if was_connected:
                        self.connection_changed.emit(False)
                        was_connected = False
                    self.error.emit(f'Не удалось загрузить превью: {error}')
                    self._sleep_interval()
                    continue

                if response.status_code == 204:
                    if was_connected:
                        self.connection_changed.emit(False)
                        was_connected = False
                    self._sleep_interval()
                    continue

                if not response.ok:
                    if was_connected:
                        self.connection_changed.emit(False)
                        was_connected = False
                    self.error.emit(
                        f'Запрос превью завершился с ошибкой: {response.status_code}'
                    )
                    self._sleep_interval()
                    continue

                image = QImage.fromData(response.content, 'JPG')
                if image.isNull():
                    self._sleep_interval()
                    continue

                if not was_connected:
                    self.connection_changed.emit(True)
                    was_connected = True

                self.frame_ready.emit(image)
                self._sleep_interval()
        finally:
            session.close()
            if was_connected:
                self.connection_changed.emit(False)

    def stop(self) -> None:
        self.requestInterruption()
        if self.isRunning():
            self.wait()

    def _sleep_interval(self) -> None:
        end_time = time.perf_counter() + self.poll_interval_seconds
        while not self.isInterruptionRequested() and time.perf_counter() < end_time:
            self.msleep(10)


def _convert_cv_frame_to_qimage(frame) -> QImage:
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, _channels = rgb_frame.shape
    bytes_per_line = rgb_frame.strides[0]
    return QImage(
        rgb_frame.data,
        width,
        height,
        bytes_per_line,
        QImage.Format.Format_RGB888,
    ).copy()


def _open_capture(*, source_type: str, capture_source: str | int) -> cv2.VideoCapture:
    normalized_type = source_type.strip().lower()
    if normalized_type not in {'webcam', 'camera'}:
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
