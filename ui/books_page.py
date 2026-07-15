"""Books Management page: list, search, filter, add/edit, delete, Excel."""

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
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import utils
from services import ServiceError, book_service, excel_service
from ui import theme


class BookFormDialog(QDialog):
    """Modal Add/Edit book form."""

    def __init__(self, parent=None, book: dict = None):
        super().__init__(parent)
        self.book = book
        self.setWindowTitle("Edit Book" if book else "Add Book")
        self.setMinimumWidth(440)
        self._build_ui()
        if book:
            self._load(book)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter book title")
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Enter author name")
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Enter book category")
        self.total_input = QSpinBox()
        self.total_input.setRange(0, 1000000)
        self.status_input = QComboBox()
        self.status_input.addItems(["ACTIVE", "INACTIVE"])

        form.addRow(self._req("Book Title"), self.title_input)
        form.addRow("Author", self.author_input)
        form.addRow("Category", self.category_input)
        form.addRow(self._req("Total Quantity"), self.total_input)
        form.addRow("Status", self.status_input)
        layout.addLayout(form)

        self.hint = QLabel("Available quantity is managed automatically.")
        self.hint.setObjectName("hintLabel")
        layout.addWidget(self.hint)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = theme.make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        save = theme.make_button("Save Book", "primary")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _req(self, text) -> QLabel:
        label = QLabel(f"{text} *")
        label.setObjectName("fieldLabel")
        return label

    def _load(self, book):
        self.title_input.setText(book.get("title") or "")
        self.author_input.setText(book.get("author") or "")
        self.category_input.setText(book.get("category") or "")
        self.total_input.setValue(int(book.get("total_quantity") or 0))
        self.status_input.setCurrentText(book.get("status") or "ACTIVE")
        issued = book_service.get_issued_count(book["id"])
        if issued:
            self.hint.setText(
                f"{issued} copy(ies) currently issued. Total cannot go below {issued}."
            )

    def _save(self):
        self.error_label.setText("")
        data = {
            "title": self.title_input.text(),
            "author": self.author_input.text(),
            "category": self.category_input.text(),
            "total_quantity": self.total_input.value(),
            "status": self.status_input.currentText(),
        }
        try:
            if self.book:
                book_service.update_book(self.book["id"], data)
            else:
                book_service.add_book(data)
            self.accept()
        except ServiceError as exc:
            self.error_label.setText(str(exc))


class BooksPage(QWidget):
    """Books Management screen."""

    COLUMNS = ["ID", "Title", "Author", "Category",
               "Total", "Available", "Availability", "Status", "Actions"]

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Books Management")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Manage all library books, quantities, and availability.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Action buttons
        actions = QHBoxLayout()
        add_btn = theme.make_button("Add Book", "primary")
        add_btn.clicked.connect(self._add_book)
        import_btn = theme.make_button("Import from Excel", "secondary")
        import_btn.clicked.connect(self._import_excel)
        export_btn = theme.make_button("Export to Excel", "success")
        export_btn.clicked.connect(self._export_excel)
        actions.addWidget(add_btn)
        actions.addWidget(import_btn)
        actions.addWidget(export_btn)
        actions.addStretch()
        layout.addLayout(actions)

        # Search + filters
        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by title, author, or category"
        )
        self.search_input.textChanged.connect(self.refresh)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "Active", "Inactive"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.avail_filter = QComboBox()
        self.avail_filter.addItems(["All", "Available", "Issued", "Low Stock"])
        self.avail_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.status_filter, 1)
        filters.addWidget(self.avail_filter, 1)
        layout.addLayout(filters)

        # Table
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hintLabel")
        layout.addWidget(self.status_label)

    # -- Data --------------------------------------------------------------
    def refresh(self):
        status_map = {"Active": "ACTIVE", "Inactive": "INACTIVE"}
        status = status_map.get(self.status_filter.currentText())
        avail_text = self.avail_filter.currentText()
        availability = {"Available": "available", "Issued": "issued"}.get(avail_text)
        low_stock = avail_text == "Low Stock"

        books = book_service.get_books(
            search=self.search_input.text(),
            status=status,
            availability=availability,
            low_stock_only=low_stock,
        )
        self._populate(books)
        self.status_label.setText(
            "No books found. Click \"Add Book\" to add your first library book."
            if not books else f"{len(books)} book(s) shown."
        )

    def _populate(self, books):
        self.table.setRowCount(0)
        for book in books:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 64)
            self.table.setItem(r, 0, self._centered_item(str(book["id"])))
            self.table.setItem(r, 1, self._centered_item(book.get("title") or ""))
            self.table.setItem(r, 2, self._centered_item(book.get("author") or ""))
            self.table.setItem(r, 3, self._centered_item(book.get("category") or ""))
            self.table.setItem(
                r, 4, self._centered_item(str(book.get("total_quantity", 0)))
            )
            self.table.setItem(
                r, 5, self._centered_item(str(book.get("available_quantity", 0)))
            )
            self.table.setCellWidget(
                r, 6, theme.badge_in_cell(book_service.availability_label(book))
            )
            self.table.setCellWidget(r, 7, theme.badge_in_cell(book.get("status", "")))
            self.table.setCellWidget(r, 8, self._actions_cell(book))
        self.table.resizeColumnsToContents()
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for col, min_w in ((6, 180), (7, 140), (8, 200)):
            if h.sectionSize(col) < min_w:
                h.resizeSection(col, min_w)

    @staticmethod
    def _centered_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _actions_cell(self, book) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(10)
        row.setAlignment(Qt.AlignCenter)

        edit = theme.make_button("Edit", "secondary")
        edit.setMinimumHeight(38)
        edit.setMinimumWidth(72)
        edit.clicked.connect(lambda _=False, b=book: self._edit_book(b))
        row.addWidget(edit)

        delete = theme.make_button("Delete", "danger")
        delete.setMinimumHeight(38)
        delete.setMinimumWidth(90)
        delete.clicked.connect(lambda _=False, b=book: self._delete_book(b))
        row.addWidget(delete)
        return container

    # -- Actions -----------------------------------------------------------
    def _add_book(self):
        dialog = BookFormDialog(self)
        if dialog.exec() == QDialog.Accepted:
            theme.show_success(self, "Book added successfully.")
            self.main_window.refresh_all()

    def _edit_book(self, book):
        fresh = book_service.get_book(book["id"])
        dialog = BookFormDialog(self, fresh)
        if dialog.exec() == QDialog.Accepted:
            theme.show_success(self, "Book updated successfully.")
            self.main_window.refresh_all()

    def _delete_book(self, book):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Delete Book")
        box.setText("Are you sure you want to permanently delete this book?")
        box.setInformativeText("This action cannot be undone.")
        delete_btn = box.addButton("Delete", QMessageBox.AcceptRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        theme._style_message_box(box)
        box.exec()
        if box.clickedButton() is not delete_btn:
            return
        try:
            book_service.delete_book(book["id"])
            theme.show_success(self, "Book deleted successfully.")
            self.main_window.refresh_all()
        except ServiceError as exc:
            theme.show_error(self, str(exc))

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Books Excel File", "", "Excel Files (*.xlsx *.xlsm)"
        )
        if not path:
            return
        try:
            summary = excel_service.import_books(path)
            theme.show_info(self, summary.as_text(), "Import Summary")
            self.main_window.refresh_all()
        except ServiceError as exc:
            theme.show_error(self, str(exc))

    def _export_excel(self):
        try:
            books = book_service.get_books(search=self.search_input.text())
            path = excel_service.export_books(books)
            theme.show_success(
                self, f"Report exported successfully.\nFile saved at:\n{path}"
            )
        except ServiceError as exc:
            theme.show_error(self, str(exc))
        except Exception:
            theme.show_error(self, "Unable to export the file. Please try again.")
