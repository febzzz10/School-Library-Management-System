"""Student Management page: list, search, filter, add/edit, delete,
view issue history, and Excel import/export."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import utils
from services import ServiceError, excel_service, student_service
from ui import theme


class StudentFormDialog(QDialog):
    """Modal Add/Edit student form."""

    def __init__(self, parent=None, student: dict = None):
        super().__init__(parent)
        self.student = student
        self.setWindowTitle("Edit Student" if student else "Add Student")
        self.setMinimumWidth(440)
        self._build_ui()
        if student:
            self._load(student)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Admission number / student ID")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter student name")
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("Enter class")
        self.division_input = QLineEdit()
        self.division_input.setPlaceholderText("Enter division")
        self.division_input.textChanged.connect(self._uppercase_division)
        self.status_input = QComboBox()
        self.status_input.addItems(["ACTIVE", "INACTIVE"])

        form.addRow(self._req("Student ID"), self.code_input)
        form.addRow(self._req("Student Name"), self.name_input)
        form.addRow("Class", self.class_input)
        form.addRow("Division", self.division_input)
        form.addRow("Status", self.status_input)
        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = theme.make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        save = theme.make_button("Save Student", "primary")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _uppercase_division(self):
        text = self.division_input.text()
        upper = text.upper()
        if upper != text:
            pos = self.division_input.cursorPosition()
            self.division_input.blockSignals(True)
            self.division_input.setText(upper)
            self.division_input.setCursorPosition(pos)
            self.division_input.blockSignals(False)

    def _req(self, text) -> QLabel:
        label = QLabel(f"{text} *")
        label.setObjectName("fieldLabel")
        return label

    def _load(self, student):
        self.code_input.setText(student.get("student_code") or "")
        self.name_input.setText(student.get("name") or "")
        self.class_input.setText(student.get("class_name") or "")
        self.division_input.setText(student.get("division") or "")
        self.status_input.setCurrentText(student.get("status") or "ACTIVE")

    def _save(self):
        self.error_label.setText("")
        data = {
            "student_code": self.code_input.text(),
            "name": self.name_input.text(),
            "class_name": self.class_input.text(),
            "division": self.division_input.text(),
            "status": self.status_input.currentText(),
        }
        try:
            if self.student:
                student_service.update_student(self.student["id"], data)
            else:
                student_service.add_student(data)
            self.accept()
        except ServiceError as exc:
            self.error_label.setText(str(exc))


class StudentHistoryDialog(QDialog):
    """Read-only dialog showing a student's full issue history."""

    def __init__(self, parent, student: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Issue History — {student.get('name')}")
        self.setMinimumSize(640, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        heading = QLabel(
            f"{student.get('name')}  ·  {student.get('student_code')}  ·  "
            f"Class {student.get('class_name') or '-'} {student.get('division') or ''}"
        )
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["Issue ID", "Book Title", "Issue Date", "Due Date", "Return Date", "Status"]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(table)

        history = student_service.get_student_history(student["id"])
        if not history:
            layout.addWidget(QLabel("This student has no issue history yet."))
        for rec in history:
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(str(rec.get("issue_id"))))
            table.setItem(r, 1, QTableWidgetItem(rec.get("book_title") or ""))
            table.setItem(r, 2, QTableWidgetItem(utils.format_display_date(rec.get("issue_date"))))
            table.setItem(r, 3, QTableWidgetItem(utils.format_display_date(rec.get("due_date"))))
            table.setItem(r, 4, QTableWidgetItem(utils.format_display_date(rec.get("return_date"))))
            table.setCellWidget(r, 5, theme.badge_in_cell(rec.get("status") or ""))
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        close = theme.make_button("Close", "secondary")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)


class StudentsPage(QWidget):
    """Student Management screen."""

    COLUMNS = ["Student ID", "Name", "Class", "Division", "Status", "Actions"]

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Student Management")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Manage student records and view issue history.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        actions = QHBoxLayout()
        add_btn = theme.make_button("Add Student", "primary")
        add_btn.clicked.connect(self._add_student)
        import_btn = theme.make_button("Import from Excel", "secondary")
        import_btn.clicked.connect(self._import_excel)
        export_btn = theme.make_button("Export to Excel", "success")
        export_btn.clicked.connect(self._export_excel)
        actions.addWidget(add_btn)
        actions.addWidget(import_btn)
        actions.addWidget(export_btn)
        actions.addStretch()
        layout.addLayout(actions)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by student ID, name, class, or division"
        )
        self.search_input.textChanged.connect(self.refresh)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Inactive"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.status_filter, 1)
        layout.addLayout(filters)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 300)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hintLabel")
        layout.addWidget(self.status_label)

    def refresh(self):
        status_map = {"Active": "ACTIVE", "Inactive": "INACTIVE"}
        status = status_map.get(self.status_filter.currentText())
        students = student_service.get_students(
            search=self.search_input.text(), status=status
        )
        self._populate(students)
        self.status_label.setText(
            "No students added yet. Click \"Add Student\" to register a student."
            if not students else f"{len(students)} student(s) shown."
        )

    def _populate(self, students):
        self.table.setRowCount(0)
        for st in students:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 64)
            self.table.setItem(r, 0, self._centered_item(st.get("student_code") or ""))
            self.table.setItem(r, 1, self._centered_item(st.get("name") or ""))
            self.table.setItem(r, 2, self._centered_item(st.get("class_name") or ""))
            self.table.setItem(r, 3, self._centered_item(st.get("division") or ""))
            self.table.setCellWidget(r, 4, theme.badge_in_cell(st.get("status", "")))
            self.table.setCellWidget(r, 5, self._actions_cell(st))
        self._fix_column_widths()

    def _fix_column_widths(self):
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 300)

    @staticmethod
    def _centered_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _actions_cell(self, student) -> QWidget:
        container = QWidget()
        container.setMinimumWidth(250)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row = QHBoxLayout(container)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(10)
        row.setAlignment(Qt.AlignCenter)

        edit = theme.make_button("Edit", "secondary")
        edit.setMinimumWidth(65)
        edit.setMinimumHeight(38)
        edit.clicked.connect(lambda _=False, s=student: self._edit_student(s))
        row.addWidget(edit)

        history = theme.make_button("History", "secondary")
        history.setMinimumWidth(85)
        history.setMinimumHeight(38)
        history.clicked.connect(lambda _=False, s=student: self._view_history(s))
        row.addWidget(history)

        delete = theme.make_button("Delete", "danger")
        delete.setMinimumWidth(90)
        delete.setMinimumHeight(38)
        delete.clicked.connect(lambda _=False, s=student: self._delete_student(s))
        row.addWidget(delete)
        return container

    # -- Actions -----------------------------------------------------------
    def _add_student(self):
        dialog = StudentFormDialog(self)
        if dialog.exec() == QDialog.Accepted:
            theme.show_success(self, "Student added successfully.")
            self.main_window.refresh_all()

    def _edit_student(self, student):
        fresh = student_service.get_student(student["id"])
        dialog = StudentFormDialog(self, fresh)
        if dialog.exec() == QDialog.Accepted:
            theme.show_success(self, "Student updated successfully.")
            self.main_window.refresh_all()

    def _view_history(self, student):
        StudentHistoryDialog(self, student).exec()

    def _delete_student(self, student):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Delete Student")
        box.setText("Are you sure you want to permanently delete this student?")
        box.setInformativeText("This action cannot be undone.")
        delete_btn = box.addButton("Delete", QMessageBox.AcceptRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        theme._style_message_box(box)
        box.exec()
        if box.clickedButton() is not delete_btn:
            return
        try:
            student_service.delete_student(student["id"])
            theme.show_success(self, "Student deleted successfully.")
            self.main_window.refresh_all()
        except ServiceError as exc:
            theme.show_error(self, str(exc))

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Students Excel File", "", "Excel Files (*.xlsx *.xlsm)"
        )
        if not path:
            return
        try:
            summary = excel_service.import_students(path)
            theme.show_info(self, summary.as_text(), "Import Summary")
            self.main_window.refresh_all()
        except ServiceError as exc:
            theme.show_error(self, str(exc))

    def _export_excel(self):
        try:
            students = student_service.get_students(search=self.search_input.text())
            path = excel_service.export_students(students)
            theme.show_success(
                self, f"Report exported successfully.\nFile saved at:\n{path}"
            )
        except ServiceError as exc:
            theme.show_error(self, str(exc))
        except Exception:
            theme.show_error(self, "Unable to export the file. Please try again.")
