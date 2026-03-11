from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from frontend.app_state import AppState
from frontend.tabs.cameras_tab import CamerasTab


class MainWindow(QMainWindow):
    '''Главное окно приложения.'''

    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self.app_state = app_state

        self.setWindowTitle('Система мониторинга камер')
        self.resize(1200, 800)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        '''Собирает интерфейс главного окна.'''
        self.tabs = QTabWidget()

        self.cameras_tab = CamerasTab(app_state=self.app_state)
        self.events_tab = self._create_placeholder_tab(
            title='События',
            text='Здесь будет список событий',
        )
        self.settings_tab = self._create_placeholder_tab(
            title='Настройки',
            text='Здесь будут настройки приложения',
        )

        self.tabs.addTab(self.cameras_tab, 'Камеры')
        self.tabs.addTab(self.events_tab, 'События')
        self.tabs.addTab(self.settings_tab, 'Настройки')

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage('Приложение запущено')

    def _create_placeholder_tab(self, title: str, text: str) -> QWidget:
        '''Создаёт временную заглушку для вкладки.'''
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title_label = QLabel(title)
        title_label.setStyleSheet('font-size: 20px; font-weight: bold;')

        text_label = QLabel(text)
        text_label.setStyleSheet('font-size: 14px; color: #666;')

        layout.addWidget(title_label)
        layout.addWidget(text_label)
        layout.addStretch()

        return tab

    def _connect_signals(self) -> None:
        '''Подключает сигналы AppState к UI.'''
        self.app_state.detection_toggled.connect(self._on_detection_toggled)

    def _on_detection_toggled(self, enabled: bool) -> None:
        '''Обрабатывает переключение режима обнаружения.'''
        status = 'ВКЛ' if enabled else 'ВЫКЛ'
        self.statusBar().showMessage(f'Обнаружение: {status}')