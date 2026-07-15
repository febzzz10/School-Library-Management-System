"""Reports page: pick a report type, filter, view, and export to Excel."""

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import utils
from services import ServiceError, excel_service, report_service, student_service
from ui import theme

REPORT_TYPES = [
    "All Books",
    "Available Books",
    "Issued Books",
    "Returned Books",
    "Pending Returns",
    "Overdue Books",
    "Low Stock Books",
    "Students",
    "Student-wise Issue History",
    "Date-wise Issue Report",
    "Date-wise Return Report",
]

REPORT_MAP = {
    "All Books": report_service.report_all_books,
    "Available Books": report_service.report_available_books,
    "Issued Books": report_service.report_issued_books,
    "Returned Books": report_service.report_returned_books,
    "Pending Returns": report_service.report_pending_returns,
    "Overdue Books": report_service.report_overdue,
    "Low Stock Books": report_service.report_low_stock,
    "Students": report_service.report_students,
    "Student-wise Issue History": None,
    "Date-wise Issue Report": report_service.report_date_wise_issue,
    "Date-wise Return Report": report_service.report_date_wise_return,
}

NEEDS_DATE_FILTER = {
    "Issued Books",
    "Returned Books",
    "Date-wise Issue Report",
    "Date-wise Return Report",
}

DATE_WISE_ONLY = {"Date-wise Issue Report", "Date-wise Return Report"}

STUDENT_HISTORY_TYPE = "Student-wise Issue History"


class ReportsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._columns = []
        self._rows = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Reports")
        title.setObjectName("pageTitle")
        subtitle = QLabel("View library reports and export them to Excel.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Report Type:"))
        self.type_combo = QComboBox()
        for r in REPORT_TYPES:
            self.type_combo.addItem(r)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        row1.addWidget(self.type_combo, 1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        row1.addWidget(self.search_input, 2)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.date_from_label = QLabel("From:")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_to_label = QLabel("To:")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())

        row2.addWidget(self.date_from_label)
        row2.addWidget(self.date_from)
        row2.addWidget(self.date_to_label)
        row2.addWidget(self.date_to)

        generate_btn = theme.make_button("Generate Report", "primary")
        generate_btn.clicked.connect(self._generate)
        self.export_btn = theme.make_button("Export to Excel", "success")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)

        row2.addStretch()
        row2.addWidget(generate_btn)
        row2.addWidget(self.export_btn)
        layout.addLayout(row2)

        self.table = QTableWidget(0, 0)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        self.student_selector = QWidget()
        sel_layout = QVBoxLayout(self.student_selector)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(6)
        sel_header = QLabel("Select a student to view their issue history:")
        sel_header.setObjectName("fieldLabel")
        sel_layout.addWidget(sel_header)
        self.student_search_input = QLineEdit()
        self.student_search_input.setPlaceholderText("Search by student ID, name, or class")
        self.student_search_input.textChanged.connect(self._search_students)
        sel_layout.addWidget(self.student_search_input)
        self.student_table = QTableWidget(0, 3)
        self.student_table.setHorizontalHeaderLabels(["Student ID", "Name", "Class"])
        self.student_table.verticalHeader().setVisible(False)
        self.student_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.student_table.setSelectionMode(QTableWidget.SingleSelection)
        self.student_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.student_table.setMaximumHeight(180)
        self.student_table.itemSelectionChanged.connect(self._on_student_selected)
        sel_layout.addWidget(self.student_table)
        self.student_selector.setVisible(False)
        layout.addWidget(self.student_selector)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hintLabel")
        layout.addWidget(self.status_label)

        self._on_type_changed()

    def _current_type(self):
        return REPORT_TYPES[self.type_combo.currentIndex()]

    def _on_type_changed(self):
        report_type = self._current_type()
        is_student_history = report_type == STUDENT_HISTORY_TYPE
        needs_date = report_type in NEEDS_DATE_FILTER
        needs_search = report_type not in DATE_WISE_ONLY and not is_student_history

        self.date_from_label.setVisible(needs_date)
        self.date_from.setVisible(needs_date)
        self.date_to_label.setVisible(needs_date)
        self.date_to.setVisible(needs_date)
        self.search_input.setVisible(needs_search)
        self.student_selector.setVisible(is_student_history)

        if is_student_history:
            self._clear_student_table()
            self._clear_main_table()
            self._search_students()

    def _generate(self):
        report_type = self._current_type()
        if report_type == STUDENT_HISTORY_TYPE:
            self._search_students()
            self._columns, self._rows = [], []
            self._render([], [])
            self.export_btn.setEnabled(False)
            self.status_label.setText("Select a student from the list above.")
            return

        func = REPORT_MAP[report_type]
        search = self.search_input.text()
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        try:
            if report_type in NEEDS_DATE_FILTER:
                if report_type in DATE_WISE_ONLY:
                    columns, rows = func(date_from, date_to)
                else:
                    columns, rows = func(search, date_from, date_to)
            else:
                columns, rows = func(search)
        except ServiceError:
            columns, rows = [], []

        self._columns, self._rows = columns, rows
        self._render(columns, rows)
        self.export_btn.setEnabled(bool(rows))
        self.status_label.setText(
            "No records found." if not rows else f"{len(rows)} record(s) found."
        )

    def _search_students(self):
        text = self.student_search_input.text()
        students = student_service.get_students(search=text)
        self._student_rows = students
        self.student_table.setRowCount(0)
        for st in students:
            r = self.student_table.rowCount()
            self.student_table.insertRow(r)
            self.student_table.setItem(r, 0, QTableWidgetItem(st.get("student_code") or ""))
            self.student_table.setItem(r, 1, QTableWidgetItem(st.get("name") or ""))
            cls = st.get("class_name") or ""
            div = st.get("division") or ""
            cls_display = f"{cls} {div}".strip()
            self.student_table.setItem(r, 2, QTableWidgetItem(cls_display))
        self.student_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _on_student_selected(self):
        row = self.student_table.currentRow()
        if row < 0 or row >= len(self._student_rows):
            return
        student = self._student_rows[row]
        columns, rows = report_service.report_student_history(student["id"])
        self._columns, self._rows = columns, rows
        self._render(columns, rows)
        self.export_btn.setEnabled(bool(rows))
        name = student.get("name", "")
        self.status_label.setText(
            "No issue history for this student." if not rows
            else f"{len(rows)} record(s) for {name}."
        )

    def _clear_student_table(self):
        self.student_table.setRowCount(0)
        self._student_rows = []

    def _clear_main_table(self):
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._columns = []
        self._rows = []

    def _render(self, columns, rows):
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(0)
        for row in rows:
            values = list(row.values())
            r = self.table.rowCount()
            self.table.insertRow(r)
            for col in range(len(columns)):
                value = values[col] if col < len(values) else ""
                if value is None:
                    value = ""
                self.table.setItem(r, col, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        if columns:
            self.table.horizontalHeader().setSectionResizeMode(
                len(columns) - 1, QHeaderView.Stretch
            )

    def _export(self):
        if not self._columns or not self._rows:
            theme.show_info(self, "No data to export.")
            return
        report_type = self._current_type()
        filename = report_type.lower().replace(" ", "_").replace("-", "_") + "_report.xlsx"
        try:
            path = excel_service.export_rows(
                self._columns, self._rows, filename,
                sheet_title=report_type[:31],
                report_title=f"{report_type} Report"
            )
            theme.show_success(
                self, f"Report exported successfully.\nFile saved at:\n{path}"
            )
        except ServiceError as exc:
            theme.show_error(self, str(exc))
        except Exception:
            theme.show_error(self, "Unable to export the report. Please try again.")
