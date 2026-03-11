from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

@dataclass
class Camera:
    id: str
    name: str
    source_url: str
    source: str
    connected: bool

class AppState(QObject):
    cameras_changed = Signal()
    selection_changed = Signal()
    detection_toggled = Signal()
    event_received = Signal()

    def __init__(self):
        super().__init__()

        self.cameras: list[Camera] = []
        self.selection_camera_id: str | None = None
        self.detection_enabled: bool = False
        self.event: list[dict] = []

    def add_camera(self, camera: Camera):
        self.cameras.append(camera)
        self.cameras_changed.emit()

    def remove_camera(self, camera_id: str):
        self.cameras = [camera for camera in self.cameras if camera.id != self.camera_id]

        if self.selection_camera_id == camera_id:
            self.selection_camera_id = None
            self.selection_changed.emit()

        self.cameras_changed.emit()

    def set_selected_camera(self, camera_id: str | None):
        self.selected_camera_id = camera_id
        self.selection_changed.emit()

    def toggle_detection(self):
        self.detection_enabled = not self.detection_enabled
        self.detection_toggled.emit(self.detection_enabled)