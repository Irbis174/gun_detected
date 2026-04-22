import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from frontend.app_state import AppState
from frontend.windows.main_window import MainWindow


def _install_russian_translations(app: QApplication) -> None:
    locale = QLocale(QLocale.Language.Russian, QLocale.Country.Russia)
    QLocale.setDefault(locale)

    translator = QTranslator(app)
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(locale, 'qtbase', '_', translations_path):
        app.installTranslator(translator)
        app._qtbase_translator = translator


def main() -> None:
    """Точка входа в приложение."""
    app = QApplication(sys.argv)
    _install_russian_translations(app)

    app_state = AppState()
    window = MainWindow(app_state=app_state)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
