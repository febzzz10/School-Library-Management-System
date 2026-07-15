"""Settings page: school/library config, and backup/restore controls."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app import utils
from services import ServiceError, backup_service, excel_service
from ui import theme


class SettingsPage(QWidget):
    """Configuration form plus backup/restore actions."""

    settings_updated = Signal(dict)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Manage school, library, and backup settings.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        columns.addWidget(self._settings_card(), 1)
        columns.addWidget(self._backup_card(), 1)
        layout.addLayout(columns)
        layout.addStretch()

    def _settings_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(12)

        header = QLabel("General Settings")
        header.setObjectName("sectionTitle")
        v.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.school_input = QLineEdit()
        self.library_input = QLineEdit()
        self.due_input = QSpinBox()
        self.due_input.setRange(1, 365)
        self.low_stock_input = QSpinBox()
        self.low_stock_input.setRange(0, 100)
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setReadOnly(True)
        self.backup_browse = QPushButton("Browse")
        self.backup_browse.setFixedWidth(80)
        self.backup_browse.clicked.connect(lambda: self._browse_folder("backup_path_input"))
        self.export_path_input = QLineEdit()
        self.export_path_input.setReadOnly(True)
        self.export_browse = QPushButton("Browse")
        self.export_browse.setFixedWidth(80)
        self.export_browse.clicked.connect(lambda: self._browse_folder("export_path_input"))

        form.addRow("School Name", self.school_input)
        form.addRow("Library Name", self.library_input)
        form.addRow("Default Due Days", self.due_input)
        form.addRow("Low Stock Limit", self.low_stock_input)

        backup_row = QHBoxLayout()
        backup_row.addWidget(self.backup_path_input, 1)
        backup_row.addWidget(self.backup_browse)
        form.addRow("Backup Folder", backup_row)

        export_row = QHBoxLayout()
        export_row.addWidget(self.export_path_input, 1)
        export_row.addWidget(self.export_browse)
        form.addRow("Export Folder", export_row)

        v.addLayout(form)

        save = theme.make_button("Save Settings", "primary")
        save.clicked.connect(self._save_settings)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(save)
        v.addLayout(row)
        return card

    def _backup_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(12)

        header = QLabel("Backup & Restore")
        header.setObjectName("sectionTitle")
        v.addWidget(header)

        self.backup_info = QLabel("")
        self.backup_info.setObjectName("hintLabel")
        self.backup_info.setWordWrap(True)
        v.addWidget(self.backup_info)

        backup_btn = theme.make_button("Backup Database", "success")
        backup_btn.clicked.connect(self._backup_database)
        v.addWidget(backup_btn)

        excel_btn = theme.make_button("Export Full Excel Backup", "success")
        excel_btn.clicked.connect(self._export_full_backup)
        v.addWidget(excel_btn)

        restore_btn = theme.make_button("Restore Backup", "danger")
        restore_btn.clicked.connect(self._restore_backup)
        v.addWidget(restore_btn)

        warning = QLabel(
            "Restoring a backup replaces all current data. "
            "A safety backup is created before restoring."
        )
        warning.setObjectName("hintLabel")
        warning.setWordWrap(True)
        v.addWidget(warning)
        v.addStretch()
        return card

    # -- Data --------------------------------------------------------------
    def refresh(self):
        settings = utils.get_all_settings()
        self.school_input.setText(settings.get("school_name", ""))
        self.library_input.setText(settings.get("library_name", ""))
        self.due_input.setValue(int(settings.get("default_due_days", 7)))
        self.low_stock_input.setValue(int(settings.get("low_stock_limit", 2)))
        self.backup_path_input.setText(settings.get("backup_path", ""))
        self.export_path_input.setText(settings.get("export_path", ""))
        self.backup_info.setText(backup_service.last_backup_display())

    def _save_settings(self):
        utils.set_setting("school_name", self.school_input.text().strip())
        utils.set_setting("library_name", self.library_input.text().strip())
        utils.set_setting("default_due_days", self.due_input.value())
        utils.set_setting("low_stock_limit", self.low_stock_input.value())
        utils.set_setting("backup_path", self.backup_path_input.text().strip())
        utils.set_setting("export_path", self.export_path_input.text().strip())
        updated = {
            "school_name": self.school_input.text().strip(),
            "library_name": self.library_input.text().strip(),
            "default_due_days": str(self.due_input.value()),
            "low_stock_limit": str(self.low_stock_input.value()),
            "backup_path": self.backup_path_input.text().strip(),
            "export_path": self.export_path_input.text().strip(),
        }
        self.settings_updated.emit(updated)
        theme.show_success(self, "Settings saved and applied successfully.")

    def _browse_folder(self, attr: str):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            getattr(self, attr).setText(path)

    def _backup_database(self):
        try:
            path = backup_service.backup_database()
            theme.show_success(
                self, f"Backup created successfully.\nFile saved at:\n{path}"
            )
            self.refresh()
        except ServiceError as exc:
            theme.show_error(self, str(exc))

    def _export_full_backup(self):
        try:
            path = excel_service.export_full_backup()
            theme.show_success(
                self,
                f"Full Excel backup created successfully.\nFile saved at:\n{path}",
            )
        except ServiceError as exc:
            theme.show_error(self, str(exc))
        except Exception:
            theme.show_error(self, "Backup failed. Please check folder permission.")

    def _restore_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup Database File", "",
            "Database Files (*.db)"
        )
        if not path:
            return
        if not theme.confirm(
            self,
            "Restoring will replace ALL current data. A safety backup will be "
            "created first. Continue?",
            ok_text="Restore",
        ):
            return
        try:
            safety = backup_service.restore_database(path)
            message = "Backup restored successfully."
            if safety:
                message += f"\n\nA safety copy of your previous data was saved at:\n{safety}"
            theme.show_success(self, message)
        except ServiceError as exc:
            theme.show_error(self, str(exc))
