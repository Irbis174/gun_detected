from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class CameraTile(QFrame):
    clicked = Signal(str)

    def __init__(self, camera_id: str, name: str, online: bool = True) -> None:
        super().__init__()

        self.camera_id = camera_id
        self.name = name
        self.online = online

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            '''
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 10px;
                background: #f7f7f7;
            }
            '''
        )

        layout = QVBoxLayout(self)

        self.name_label = QLabel(name)
        self.status_label = QLabel('В сети' if online else 'Не в сети')
        self.preview_label = QLabel('Здесь будет превью')
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setStyleSheet('background: #e9e9e9; border-radius: 8px;')

        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.preview_label)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.camera_id)
        super().mousePressEvent(event)
