from __future__ import annotations

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.app_state import AppState, Camera
from frontend.backend_client import BackendClient, BackendClientError
from frontend.i18n import (
    build_detection_alert_message,
    build_detection_event_summary,
    translate_detection_label,
)
from frontend.widgets.camera_tile import CameraTile


class CamerasTab(QWidget):
    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self.app_state = app_state
        self.backend = BackendClient()
        self.tiles: dict[str, CameraTile] = {}
        self._announced_detection_ids: set[int] = set()

        self._build_ui()
        self._connect_signals()
        self._load_sources()
        self._start_polling()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #12161c;
                color: #eff4fb;
            }
            QLabel#tabTitle {
                font-size: 22px;
                font-weight: 700;
                color: #f4f7fb;
            }
            QLabel#emptyState {
                color: #aab4c3;
                font-size: 14px;
                padding: 40px;
                border: 1px dashed #2d3642;
                border-radius: 12px;
                background: #171b21;
            }
            QWidget#toolbar {
                background: #171b21;
                border: 1px solid #2a313b;
                border-radius: 12px;
            }
            QPushButton {
                min-height: 38px;
                border-radius: 10px;
                border: 1px solid #36404c;
                background: #27303a;
                color: #f4f7fb;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #313b47;
            }
            """
        )

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(14)

        self.title_label = QLabel('Камеры')
        self.title_label.setObjectName('tabTitle')
        self.root_layout.addWidget(self.title_label)

        self.toolbar_widget = QWidget()
        self.toolbar_widget.setObjectName('toolbar')
        self.toolbar_layout = QHBoxLayout(self.toolbar_widget)
        self.toolbar_layout.setContentsMargins(12, 12, 12, 12)
        self.toolbar_layout.setSpacing(10)

        self.add_file_button = QPushButton('Добавить файл')
        self.add_file_button.clicked.connect(self._on_add_file)

        self.add_webcam_button = QPushButton('Добавить веб-камеру')
        self.add_webcam_button.clicked.connect(self._on_add_webcam)

        self.refresh_button = QPushButton('Обновить')
        self.refresh_button.clicked.connect(self._load_sources)

        self.toggle_button = QPushButton(
            'Обнаружение: включено'
            if self.app_state.detection_enabled
            else 'Обнаружение: выключено'
        )
        self.toggle_button.clicked.connect(self.app_state.toggle_detection)

        self.toolbar_layout.addWidget(self.add_file_button)
        self.toolbar_layout.addWidget(self.add_webcam_button)
        self.toolbar_layout.addWidget(self.refresh_button)
        self.toolbar_layout.addWidget(self.toggle_button)
        self.toolbar_layout.addStretch()
        self.root_layout.addWidget(self.toolbar_widget)

        self.empty_state = QLabel(
            'Пока нет источников. Добавьте видеофайл или подключите веб-камеру.'
        )
        self.empty_state.setObjectName('emptyState')
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root_layout.addWidget(self.empty_state)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet('QScrollArea { border: none; background: transparent; }')

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet('background: transparent;')
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(14)
        self.grid_layout.setVerticalSpacing(14)
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.scroll_area.setWidget(self.grid_container)
        self.root_layout.addWidget(self.scroll_area, 1)

        self._update_empty_state()

    def _connect_signals(self) -> None:
        self.app_state.cameras_changed.connect(self._sync_tiles)
        self.app_state.camera_updated.connect(self._update_tile)
        self.app_state.detection_toggled.connect(self._on_detection_toggled)

    def _start_polling(self) -> None:
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(300)
        self.poll_timer.timeout.connect(self._poll_backend)
        self.poll_timer.start()

    def _load_sources(self) -> None:
        try:
            sources = self.backend.list_sources()
        except BackendClientError as error:
            self._show_error('Не удалось загрузить источники', str(error))
            return

        previous_by_source_id = {
            camera.source_id: camera for camera in self.app_state.cameras
        }
        cameras = [
            self._camera_from_source(
                source=source,
                previous=previous_by_source_id.get(source['source_id']),
            )
            for source in sources
        ]
        self.app_state.set_cameras(cameras)

    def _camera_from_source(self, *, source: dict, previous: Camera | None = None) -> Camera:
        return Camera(
            id=f"source_{source['source_id']}",
            source_id=source['source_id'],
            name=source['name'],
            source_type=source['source_type'],
            source=source['source'],
            connected=source.get('connected', False),
            test_run_id=previous.test_run_id if previous else None,
            test_run_status=previous.test_run_status if previous else None,
            processed_frames=previous.processed_frames if previous else 0,
            detections_count=previous.detections_count if previous else 0,
            latest_detection=previous.latest_detection if previous else None,
            latest_tracking_update=previous.latest_tracking_update if previous else None,
        )

    def _sync_tiles(self) -> None:
        camera_ids = {camera.id for camera in self.app_state.cameras}

        for camera_id in list(self.tiles):
            if camera_id not in camera_ids:
                tile = self.tiles.pop(camera_id)
                tile.dispose()
                self.grid_layout.removeWidget(tile)
                tile.deleteLater()

        for index, camera in enumerate(self.app_state.cameras):
            tile = self.tiles.get(camera.id)
            if tile is None:
                tile = CameraTile(camera, self)
                tile.start_requested.connect(self._start_processing)
                tile.stop_requested.connect(self._stop_processing)
                tile.delete_requested.connect(self._delete_camera)
                self.tiles[camera.id] = tile

            tile.apply_camera(camera)
            row = index // 2
            col = index % 2
            self.grid_layout.addWidget(tile, row, col)

        self._update_empty_state()

    def _update_tile(self, camera_id: str) -> None:
        tile = self.tiles.get(camera_id)
        camera = self.app_state.get_camera(camera_id)
        if tile is None or camera is None:
            return
        tile.apply_camera(camera)

    def _update_empty_state(self) -> None:
        has_cameras = bool(self.app_state.cameras)
        self.empty_state.setVisible(not has_cameras)
        self.scroll_area.setVisible(has_cameras)

    def _on_add_file(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            'Выберите видеофайл',
            '',
            'Видеофайлы (*.mp4 *.avi *.mov *.mkv);;Все файлы (*.*)',
        )
        if not file_path:
            return

        try:
            source = self.backend.create_source(
                name=os.path.basename(file_path),
                source_type='file',
                source=file_path,
            )
        except BackendClientError as error:
            self._show_error('Не удалось добавить файл', str(error))
            return

        camera = self._camera_from_source(source=source)
        self.app_state.add_camera(camera)
        self._start_processing(camera.id)

    def _on_add_webcam(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        index, ok = QInputDialog.getInt(
            self,
            'Подключение веб-камеры',
            'Индекс устройства:',
            value=0,
            minValue=0,
            maxValue=10,
        )
        if not ok:
            return

        try:
            source = self.backend.create_source(
                name=f'Веб-камера {index}',
                source_type='webcam',
                source=str(index),
            )
        except BackendClientError as error:
            self._show_error('Не удалось подключить веб-камеру', str(error))
            return

        camera = self._camera_from_source(source=source)
        self.app_state.add_camera(camera)
        self._start_processing(camera.id)

    def _start_processing(self, camera_id: str) -> None:
        camera = self.app_state.get_camera(camera_id)
        if camera is None:
            return

        restore_status = camera.test_run_status

        try:
            if camera.test_run_id is None or camera.test_run_status in {
                None,
                'finished',
                'failed',
                'stopped',
            }:
                test_run = self.backend.create_test_run(source_id=camera.source_id)
                self.app_state.update_camera(
                    camera_id,
                    test_run_id=test_run['test_run_id'],
                    test_run_status=test_run['status'],
                    processed_frames=test_run['processed_frames'],
                    detections_count=test_run['detections_count'],
                    latest_detection=None,
                    latest_tracking_update=None,
                )
                camera = self.app_state.get_camera(camera_id)
                if camera is None or camera.test_run_id is None:
                    return
                restore_status = camera.test_run_status

            if camera.source_type.strip().lower() in {'webcam', 'camera'}:
                self.app_state.update_camera(camera_id, test_run_status='scheduled')
                camera = self.app_state.get_camera(camera_id)
                if camera is None or camera.test_run_id is None:
                    return

            response = self.backend.execute_test_run(
                test_run_id=camera.test_run_id,
                sample_every=1,
            )
        except BackendClientError as error:
            self.app_state.update_camera(camera_id, test_run_status=restore_status)
            self._show_error('Не удалось запустить обработку', str(error))
            return

        self.app_state.update_camera(
            camera_id,
            test_run_status=response['status'],
            processed_frames=response['processed_frames'],
            detections_count=response['detections_count'],
        )

    def _stop_processing(self, camera_id: str) -> None:
        camera = self.app_state.get_camera(camera_id)
        if camera is None or camera.test_run_id is None:
            return

        try:
            response = self.backend.stop_test_run(test_run_id=camera.test_run_id)
        except BackendClientError as error:
            self._show_error('Не удалось остановить обработку', str(error))
            return

        self.app_state.update_camera(camera_id, test_run_status=response['status'])

    def _delete_camera(self, camera_id: str) -> None:
        camera = self.app_state.get_camera(camera_id)
        if camera is None:
            return

        if not self._confirm_delete(camera.name):
            return

        if camera.test_run_id is not None and camera.test_run_status in {
            'scheduled',
            'running',
            'stopping',
        }:
            try:
                self.backend.stop_test_run(test_run_id=camera.test_run_id)
            except BackendClientError:
                pass

        try:
            self.backend.delete_source(source_id=camera.source_id)
        except BackendClientError as error:
            self._show_error('Не удалось удалить источник', str(error))
            return

        self.app_state.remove_camera(camera_id)

    def _poll_backend(self) -> None:
        for camera in self.app_state.cameras:
            if camera.test_run_id is None:
                continue

            try:
                test_run = self.backend.get_test_run(test_run_id=camera.test_run_id)
                detections = self.backend.get_test_run_detections(
                    test_run_id=camera.test_run_id
                )
                tracking_updates = self.backend.get_tracking_updates(
                    test_run_id=camera.test_run_id,
                    latest_only=True,
                )
            except BackendClientError:
                continue

            latest_detection = detections[-1] if detections else None
            latest_tracking_update = tracking_updates[-1] if tracking_updates else None

            self.app_state.update_camera(
                camera.id,
                test_run_status=test_run['status'],
                processed_frames=test_run['processed_frames'],
                detections_count=test_run['detections_count'],
                latest_detection=latest_detection,
                latest_tracking_update=latest_tracking_update,
            )
            self._handle_confirmed_detections(camera=camera, detections=detections)

    def _on_detection_toggled(self, enabled: bool) -> None:
        self.toggle_button.setText(
            'Обнаружение: включено' if enabled else 'Обнаружение: выключено'
        )

    def _show_error(self, title: str, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.addButton('Закрыть', QMessageBox.ButtonRole.AcceptRole)
        dialog.exec()

    def _confirm_delete(self, camera_name: str) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle('Удаление источника')
        dialog.setText(f'Удалить "{camera_name}" из приложения?')
        delete_button = dialog.addButton('Удалить', QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton('Отмена', QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        return dialog.clickedButton() is delete_button

    def _handle_confirmed_detections(
        self,
        *,
        camera: Camera,
        detections: list[dict],
    ) -> None:
        for detection in detections:
            detection_id = detection.get('detection_id')
            if not isinstance(detection_id, int):
                continue
            if detection_id in self._announced_detection_ids:
                continue

            self._announced_detection_ids.add(detection_id)
            label = detection.get('label')
            score = detection.get('score')
            translated_label = translate_detection_label(
                label if isinstance(label, str) else None
            )
            self.app_state.add_event(
                {
                    'kind': 'danger_detection',
                    'title': 'Обнаружен опасный предмет',
                    'message': build_detection_alert_message(
                        camera_name=camera.name,
                        label=label if isinstance(label, str) else None,
                        score=score if isinstance(score, (float, int)) else None,
                    ),
                    'summary': build_detection_event_summary(
                        camera_name=camera.name,
                        label=label if isinstance(label, str) else None,
                        score=score if isinstance(score, (float, int)) else None,
                    ),
                    'status_message': (
                        f'Камера "{camera.name}": подтверждено обнаружение '
                        f'объекта "{translated_label}".'
                    ),
                    'camera_id': camera.id,
                    'camera_name': camera.name,
                    'detection_id': detection_id,
                }
            )

    def closeEvent(self, event) -> None:
        self.poll_timer.stop()
        for tile in self.tiles.values():
            tile.dispose()
        super().closeEvent(event)
