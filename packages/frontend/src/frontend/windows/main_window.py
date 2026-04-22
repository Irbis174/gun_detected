from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from frontend.app_state import AppState
from frontend.tabs.cameras_tab import CamerasTab


class MainWindow(QMainWindow):
    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self.app_state = app_state

        self.setWindowTitle('Мониторинг камер')
        self.resize(1400, 900)
        self._apply_theme()
        self._build_ui()
        self._connect_signals()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #0f1318;
            }
            QTabWidget::pane {
                border: 1px solid #232b35;
                background: #12161c;
            }
            QTabBar::tab {
                background: #171b21;
                color: #cfd8e3;
                padding: 10px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: #232b35;
                color: #f4f7fb;
            }
            QStatusBar {
                background: #171b21;
                color: #c5d0df;
            }
            QLabel#placeholderTitle {
                font-size: 20px;
                font-weight: 700;
                color: #f4f7fb;
            }
            QLabel#placeholderText {
                font-size: 14px;
                color: #aab4c3;
            }
            QListWidget {
                background: #171b21;
                border: 1px solid #2a313b;
                border-radius: 12px;
                color: #eff4fb;
                padding: 6px;
            }
            QListWidget::item {
                border-bottom: 1px solid #232b35;
                padding: 10px 8px;
            }
            """
        )

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()

        self.cameras_tab = CamerasTab(app_state=self.app_state)
        self.events_tab = self._create_events_tab()
        self.settings_tab = self._create_placeholder_tab(
            title='Настройки',
            text='Здесь будут отображаться настройки приложения.',
        )

        self.tabs.addTab(self.cameras_tab, 'Камеры')
        self.tabs.addTab(self.events_tab, 'События')
        self.tabs.addTab(self.settings_tab, 'Настройки')

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage('Приложение запущено')

    def _create_placeholder_tab(self, title: str, text: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title_label = QLabel(title)
        title_label.setObjectName('placeholderTitle')

        text_label = QLabel(text)
        text_label.setObjectName('placeholderText')
        text_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(text_label)
        layout.addStretch()

        return tab

    def _create_events_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title_label = QLabel('События')
        title_label.setObjectName('placeholderTitle')

        text_label = QLabel('Здесь появляются подтвержденные обнаружения и предупреждения.')
        text_label.setObjectName('placeholderText')
        text_label.setWordWrap(True)

        self.events_empty_label = QLabel('Пока событий нет.')
        self.events_empty_label.setObjectName('placeholderText')

        self.events_list = QListWidget()
        self.events_list.setVisible(False)

        layout.addWidget(title_label)
        layout.addWidget(text_label)
        layout.addWidget(self.events_empty_label)
        layout.addWidget(self.events_list, 1)

        self._refresh_events_tab()
        return tab

    def _connect_signals(self) -> None:
        self.app_state.detection_toggled.connect(self._on_detection_toggled)
        self.app_state.event_received.connect(self._on_event_received)

    def _on_detection_toggled(self, enabled: bool) -> None:
        status = 'включено' if enabled else 'выключено'
        self.statusBar().showMessage(f'Обнаружение: {status}')

    def _on_event_received(self) -> None:
        self._refresh_events_tab()
        if not self.app_state.events:
            return

        event = self.app_state.events[-1]
        status_message = str(event.get('status_message') or 'Получено новое событие.')
        self.statusBar().showMessage(status_message, 10000)

        if event.get('kind') == 'danger_detection':
            self._show_danger_alert(
                title=str(event.get('title') or 'Обнаружен опасный предмет'),
                message=str(
                    event.get('message') or 'Подтверждено обнаружение опасного предмета.'
                ),
            )

    def _refresh_events_tab(self) -> None:
        self.events_list.clear()

        for event in reversed(self.app_state.events):
            summary = str(event.get('summary') or 'Новое событие')
            self.events_list.addItem(QListWidgetItem(summary))

        has_events = bool(self.app_state.events)
        self.events_empty_label.setVisible(not has_events)
        self.events_list.setVisible(has_events)

    def _show_danger_alert(self, *, title: str, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.addButton('Понятно', QMessageBox.ButtonRole.AcceptRole)
        dialog.exec()
