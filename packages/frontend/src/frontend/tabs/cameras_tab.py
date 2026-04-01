from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.app_state import AppState, Camera


class CamerasTab(QWidget):
    """Вкладка камер."""

    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self.app_state = app_state

        self._build_ui()
        self._connect_signals()
        self.refresh_view()

    def _build_ui(self) -> None:
        """Собирает интерфейс вкладки."""
        self.root_layout = QVBoxLayout(self)

        self.title_label = QLabel("Камеры")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.root_layout.addWidget(self.title_label)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.root_layout.addWidget(self.content_widget)

    def _connect_signals(self) -> None:
        """Подключает сигналы состояния."""
        self.app_state.cameras_changed.connect(self.refresh_view)
        self.app_state.detection_toggled.connect(lambda _enabled: self.refresh_view())

    def refresh_view(self) -> None:
        """Перестраивает содержимое вкладки."""
        self._clear_layout(self.content_layout)

        if not self.app_state.cameras:
            self._build_empty_state()
        else:
            self._build_cameras_grid()

    def _build_empty_state(self) -> None:
        """Показывает экран, когда камер нет."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Пока нет подключённых камер")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")

        subtitle = QLabel(
            "Добавь первую камеру, чтобы начать просмотр и обработку."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 14px; color: #666;")

        add_button = QPushButton("Добавить тестовую камеру")
        add_button.setFixedWidth(220)
        add_button.clicked.connect(self._on_add_test_camera)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.content_layout.addStretch()
        self.content_layout.addWidget(container)
        self.content_layout.addStretch()

    def _build_cameras_grid(self) -> None:
        """Показывает сетку камер."""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)

        add_button = QPushButton("Добавить камеру")
        add_button.clicked.connect(self._on_add_test_camera)

        toggle_button = QPushButton(
            "Обнаружение: ВКЛ"
            if self.app_state.detection_enabled
            else "Обнаружение: ВЫКЛ"
        )
        toggle_button.clicked.connect(self.app_state.toggle_detection)

        toolbar_layout.addWidget(add_button)
        toolbar_layout.addWidget(toggle_button)
        toolbar_layout.addStretch()

        self.content_layout.addWidget(toolbar_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)

        columns = 2
        for index, camera in enumerate(self.app_state.cameras):
            row = index // columns
            col = index % columns
            tile = self._create_camera_tile(camera)
            grid_layout.addWidget(tile, row, col)

        scroll_area.setWidget(grid_container)
        self.content_layout.addWidget(scroll_area)

    def _create_camera_tile(self, camera: Camera) -> QWidget:
        """Создаёт простую плитку камеры."""
        tile = QWidget()
        tile.setStyleSheet(
            """
            QWidget {
                border: 1px solid #cccccc;
                border-radius: 10px;
                background: #f7f7f7;
            }
            """
        )

        layout = QVBoxLayout(tile)

        name_label = QLabel(camera.name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        status_text = "Онлайн" if camera.connected else "Оффлайн"
        status_label = QLabel(f"Статус: {status_text}")

        preview = QLabel("Здесь будет превью камеры")
        preview.setMinimumHeight(180)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet(
            """
            background: #e9e9e9;
            border-radius: 8px;
            color: #666;
            """
        )

        layout.addWidget(name_label)
        layout.addWidget(status_label)
        layout.addWidget(preview)

        return tile

    def _on_add_test_camera(self) -> None:
        next_index = len(self.app_state.cameras) + 1
        camera = Camera(
            id=f"cam_{next_index}",
            name=f"Камера {next_index}",
            source_url=f"rtsp://camera-{next_index}",
            source=str(next_index),
            connected=True,
        )
        self.app_state.add_camera(camera)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        """Очищает layout со всеми дочерними элементами."""
        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            child_layout = item.layout()

            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                CamerasTab._clear_layout(child_layout)
