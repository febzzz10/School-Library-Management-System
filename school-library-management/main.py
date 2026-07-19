"""School Library Management System — application entry point."""

import ctypes
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from app import config, database
from ui.main_window import MainWindow
from ui.theme import global_stylesheet, show_error


def _setup_logging() -> str:
    """Configure file logging in the app-data /logs folder.

    Returns the log path so it can be shown in error dialogs.
    """
    log_dir = Path(config.DATA_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"startup_{datetime.now():%Y-%m-%d}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stderr) if not getattr(sys, "frozen", False) else
            logging.NullHandler(),
        ],
    )
    return str(log_file)


class _SplashWidget(QWidget):
    """Custom splash screen with logo, title, and loading message."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 300)
        self.setStyleSheet("background: #1F1F1F; border-radius: 16px;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        logo_path = config.LOGO_PATH
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                logo = QLabel()
                logo.setPixmap(pix.scaled(130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo.setAlignment(Qt.AlignCenter)
                layout.addWidget(logo)

        title = QLabel(config.APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: 700; background: transparent;")
        layout.addWidget(title)

        self.msg = QLabel("Loading application...")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet("color: #9CA3AF; font-size: 13px; background: transparent;")
        layout.addWidget(self.msg)

    def set_message(self, text: str):
        self.msg.setText(text)


if __name__ == "__main__":
    log_path = _setup_logging()
    logging.info("=== Starting %s ===", config.APP_NAME)

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DVNS.SchoolLibraryManagementSystem.1.0"
            )
        except Exception:
            logging.warning("Could not set AppUserModelID", exc_info=True)

    try:
        database.initialize_database()
        database.check_integrity()
        logging.info("Database ready at %s", config.DATABASE_PATH)
    except Exception as exc:
        logging.critical("Database initialisation failed", exc_info=True)
        show_error(
            None,
            f"Could not prepare the database.\n\n{exc}\n\nLog: {log_path}",
            "Startup Error",
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyleSheet(global_stylesheet())

    icon_path = config.APP_ICON_PATH
    app_icon = QIcon()
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    splash = _SplashWidget()
    splash.set_message("Initializing interface...")
    splash.show()
    app.processEvents()

    try:
        window = MainWindow()
        if not app_icon.isNull():
            window.setWindowIcon(app_icon)
    except Exception as exc:
        logging.critical("MainWindow creation failed", exc_info=True)
        show_error(
            None,
            f"Failed to create the application window.\n\n{exc}\n\nLog: {log_path}",
            "Startup Error",
        )
        sys.exit(1)

    splash.set_message("Ready.")
    app.processEvents()
    window.show()
    splash.close()

    logging.info("Application started successfully")
    sys.exit(app.exec())
