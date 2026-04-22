from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal


@dataclass
class Camera:
    id: str
    source_id: int
    name: str
    source_type: str
    source: str
    connected: bool = False
    test_run_id: int | None = None
    test_run_status: str | None = None
    processed_frames: int = 0
    detections_count: int = 0
    latest_detection: dict[str, Any] | None = None
    latest_tracking_update: dict[str, Any] | None = None


class AppState(QObject):
    cameras_changed = Signal()
    camera_updated = Signal(str)
    selection_changed = Signal()
    detection_toggled = Signal(bool)
    event_received = Signal()

    def __init__(self):
        super().__init__()

        self.cameras: list[Camera] = []
        self.selection_camera_id: str | None = None
        self.detection_enabled: bool = False
        self.events: list[dict[str, Any]] = []

    def set_cameras(self, cameras: list[Camera]) -> None:
        self.cameras = cameras
        self.cameras_changed.emit()

    def add_camera(self, camera: Camera) -> None:
        self.cameras.append(camera)
        self.cameras_changed.emit()

    def remove_camera(self, camera_id: str) -> None:
        self.cameras = [camera for camera in self.cameras if camera.id != camera_id]

        if self.selection_camera_id == camera_id:
            self.selection_camera_id = None
            self.selection_changed.emit()

        self.cameras_changed.emit()

    def get_camera(self, camera_id: str) -> Camera | None:
        for camera in self.cameras:
            if camera.id == camera_id:
                return camera
        return None

    def update_camera(self, camera_id: str, **fields: Any) -> None:
        camera = self.get_camera(camera_id)
        if camera is None:
            return

        for field_name, value in fields.items():
            if hasattr(camera, field_name):
                setattr(camera, field_name, value)

        self.camera_updated.emit(camera_id)

    def set_selected_camera(self, camera_id: str | None) -> None:
        self.selection_camera_id = camera_id
        self.selection_changed.emit()

    def toggle_detection(self) -> None:
        self.detection_enabled = not self.detection_enabled
        self.detection_toggled.emit(self.detection_enabled)

    def add_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        self.event_received.emit()
