from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from frontend.app_state import Camera
from frontend.i18n import (
    translate_detection_label,
    translate_preview_source,
    translate_preview_state,
    translate_run_status,
    translate_source_type,
)
from frontend.video_feed import BackendPreviewThread, VideoFeedThread
from frontend.widgets.video_preview import VideoPreviewLabel


class CameraTile(QWidget):
    start_requested = Signal(str)
    stop_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self._preview_connected = False
        self._preview_mode: str | None = None

        self.setStyleSheet(
            """
            QWidget {
                background: #171b21;
                border: 1px solid #2a313b;
                border-radius: 14px;
                color: #eff4fb;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: 700;
                color: #f4f7fb;
                background: #20262f;
                border: 1px solid #2d3642;
                border-radius: 10px;
                padding: 10px 12px;
            }
            QLabel#meta {
                color: #c5d0df;
                background: #20262f;
                border: 1px solid #2d3642;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QPushButton {
                min-height: 38px;
                border-radius: 10px;
                border: 1px solid #36404c;
                background: #27303a;
                color: #f4f7fb;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #313b47;
            }
            QPushButton:disabled {
                background: #20262f;
                color: #748093;
                border-color: #2a313b;
            }
            QPushButton#startButton {
                background: #1f6f4a;
                border-color: #2c8d5f;
            }
            QPushButton#startButton:hover {
                background: #258659;
            }
            QPushButton#stopButton {
                background: #6b2a2a;
                border-color: #964141;
            }
            QPushButton#stopButton:hover {
                background: #7b3131;
            }
            QPushButton#deleteButton {
                background: #4d2b38;
                border-color: #7d495d;
            }
            QPushButton#deleteButton:hover {
                background: #613646;
            }
            """
        )

        self._build_ui()
        self.apply_camera(camera)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.name_label = QLabel()
        self.name_label.setObjectName('title')

        self.status_label = QLabel()
        self.status_label.setObjectName('meta')

        self.meta_label = QLabel()
        self.meta_label.setObjectName('meta')
        self.meta_label.setWordWrap(True)

        self.stats_label = QLabel()
        self.stats_label.setObjectName('meta')
        self.stats_label.setWordWrap(True)

        self.preview = VideoPreviewLabel(self)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.start_button = QPushButton('Запустить')
        self.start_button.setObjectName('startButton')
        self.start_button.clicked.connect(lambda: self.start_requested.emit(self.camera.id))

        self.stop_button = QPushButton('Остановить')
        self.stop_button.setObjectName('stopButton')
        self.stop_button.clicked.connect(lambda: self.stop_requested.emit(self.camera.id))

        self.delete_button = QPushButton('Удалить')
        self.delete_button.setObjectName('deleteButton')
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.camera.id))

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.delete_button)

        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.preview, 1)
        layout.addLayout(buttons_layout)

    def stop_preview(self) -> None:
        if hasattr(self, '_preview_thread') and self._preview_thread is not None:
            self._preview_thread.stop()
            self._preview_thread = None
        self._preview_connected = False
        self._preview_mode = None

    def _is_live_camera(self) -> bool:
        return self.camera.source_type.strip().lower() in {'webcam', 'camera'}

    def _wants_backend_preview(self) -> bool:
        return self._is_live_camera() and self.camera.test_run_status in {
            'scheduled',
            'running',
            'stopping',
        }

    def _ensure_preview_mode(self) -> None:
        desired_mode = 'backend' if self._wants_backend_preview() else 'local'
        if (
            self._preview_mode == desired_mode
            and hasattr(self, '_preview_thread')
            and self._preview_thread is not None
            and self._preview_thread.isRunning()
        ):
            return

        self.stop_preview()
        self.preview.clear_frame()
        if desired_mode == 'backend':
            self.preview.setText('Ожидание превью с сервера...')
        else:
            self.preview.setText('Превью недоступно')

        if desired_mode == 'backend':
            self._preview_thread = BackendPreviewThread(
                source_id=self.camera.source_id,
                parent=self,
            )
        else:
            self._preview_thread = VideoFeedThread(
                source_type=self.camera.source_type,
                source=self.camera.source,
                parent=self,
            )

        self._preview_thread.frame_ready.connect(self.preview.set_frame)
        self._preview_thread.connection_changed.connect(self._on_connection_changed)
        self._preview_thread.error.connect(self._on_preview_error)
        self._preview_thread.start()
        self._preview_mode = desired_mode

    def apply_camera(self, camera: Camera) -> None:
        self.camera = camera
        self._ensure_preview_mode()
        self.name_label.setText(camera.name)

        run_status = translate_run_status(camera.test_run_status)
        preview_status = translate_preview_state(self._preview_connected)
        preview_source = translate_preview_source(self._preview_mode)
        self.status_label.setText(
            f'Превью: {preview_status} ({preview_source}) | Обработка: {run_status}'
        )
        self.meta_label.setText(
            f'Источник: {translate_source_type(camera.source_type)} | '
            f'id={camera.source_id} | значение={camera.source}'
        )

        overlay = camera.latest_tracking_update or camera.latest_detection
        overlay_label = 'нет'
        if overlay:
            overlay_label = translate_detection_label(
                str(overlay.get('label') or 'опасный предмет')
            )

        self.stats_label.setText(
            f'Кадров: {camera.processed_frames} | '
            f'Подтвержденных обнаружений: {camera.detections_count} | '
            f'Последний объект: {overlay_label}'
        )
        self.preview.set_overlay(overlay)

        startable_statuses = {None, 'created', 'finished', 'failed', 'stopped'}
        stoppable_statuses = {'scheduled', 'running', 'stopping'}
        self.start_button.setEnabled(camera.test_run_status in startable_statuses)
        self.stop_button.setEnabled(camera.test_run_status in stoppable_statuses)
        self.delete_button.setEnabled(True)

    def _on_connection_changed(self, connected: bool) -> None:
        self._preview_connected = connected
        self.apply_camera(self.camera)

    def _on_preview_error(self, message: str) -> None:
        if not self._preview_connected:
            self.preview.setText(message)

    def closeEvent(self, event) -> None:
        self.stop_preview()
        super().closeEvent(event)
