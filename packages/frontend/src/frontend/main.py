import sys

from PySide6.QtWidgets import QApplication

from frontend.app_state import AppState
from frontend.windows.main_window import MainWindow


def main() -> None:
    '''Точка входа в приложение.'''
    app = QApplication(sys.argv)

    app_state = AppState()
    window = MainWindow(app_state=app_state)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()