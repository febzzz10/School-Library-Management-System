"""Main application window: sidebar navigation, page stack, and top bar."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import config, utils
from services import backup_service, excel_service
from ui.theme import LogoLabel

SIDEBAR_BG = "#071C43"
NAV_ACTIVE_BG = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #246BFD, stop:1 #1556D8)"

# ---------------------------------------------------------------------------
# Page imports — gracefully degrade to placeholder for any that don't exist
# ---------------------------------------------------------------------------
try:
    from ui.dashboard import DashboardPage
except ImportError:
    DashboardPage = None

try:
    from ui.books_page import BooksPage
except ImportError:
    BooksPage = None

try:
    from ui.students_page import StudentsPage
except ImportError:
    StudentsPage = None

try:
    from ui.issue_book_page import IssueBookPage
except ImportError:
    IssueBookPage = None

try:
    from ui.return_book_page import ReturnBookPage
except ImportError:
    ReturnBookPage = None

try:
    from ui.reports_page import ReportsPage
except ImportError:
    ReportsPage = None

try:
    from ui.settings_page import SettingsPage
except ImportError:
    SettingsPage = None

# ---------------------------------------------------------------------------
# Sidebar entries
# ---------------------------------------------------------------------------
NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("Books Management", "books"),
    ("Student Management", "students"),
    ("Issue Book", "issue"),
    ("Return Book", "return"),
    ("Reports", "reports"),
    ("Settings", "settings"),
]

class PlaceholderPage(QWidget):
    """Fallback shown when a page module is not yet created."""

    def __init__(self, title: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        label = QLabel(f"{title} — Coming Soon")
        label.setObjectName("pageTitle")
        layout.addWidget(label)


class MainWindow(QMainWindow):
    """Top-level window hosting the sidebar and stacked pages."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME}  v{config.APP_VERSION}")
        self.resize(1200, 760)
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content(), 1)
        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)

        if hasattr(self, "settings") and hasattr(self.settings, "settings_updated"):
            self.settings.settings_updated.connect(self.apply_updated_settings)

        self._select_page(0)

    # -- Top bar ------------------------------------------------------------
    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E3EAF5;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel(config.APP_NAME)
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827; background: transparent;")
        layout.addWidget(title)

        layout.addStretch()

        logo_small = LogoLabel(32)
        layout.addWidget(logo_small)

        self.top_right = QLabel()
        self.top_right.setObjectName("topBarRight")
        layout.addWidget(self.top_right)
        self._refresh_top_bar()

        return bar

    # -- Sidebar ------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background: {SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo = LogoLabel(56)
        layout.addWidget(logo, alignment=Qt.AlignCenter)

        self.brand = QLabel("School Library")
        self.brand.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 700; padding: 8px 18px 0;")
        self.brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.brand)

        sub = QLabel("Management System")
        sub.setStyleSheet("color: #9CA3AF; font-size: 12px; padding: 2px 18px 12px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background: #1E3A6F; max-height: 1px; margin: 4px 18px;")
        layout.addWidget(divider)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (label, _) in enumerate(NAV_ITEMS):
            button = QPushButton(f"  {label}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(
                f"""
                QPushButton#navButton {{
                    color: #B0BEC5; background: transparent; border: none;
                    text-align: left; padding: 11px 18px; font-size: 13px;
                    margin: 2px 10px; border-radius: 8px;
                }}
                QPushButton#navButton:hover {{
                    background: #0F2D5E; color: #FFFFFF;
                }}
                QPushButton#navButton:checked {{
                    background: {NAV_ACTIVE_BG}; color: #FFFFFF; font-weight: 600;
                }}
                """
            )
            button.clicked.connect(lambda _=False, i=index: self._select_page(i))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)

        layout.addStretch()

        version = QLabel(f"Version {config.APP_VERSION}")
        version.setStyleSheet("color: #6B7280; font-size: 11px; padding: 12px 18px;")
        layout.addWidget(version)

        return sidebar

    # -- Content stack ------------------------------------------------------
    def _build_content(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("contentArea")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.pages = []

        page_specs = [
            ("dashboard", DashboardPage, "Dashboard"),
            ("books", BooksPage, "Books Management"),
            ("students", StudentsPage, "Student Management"),
            ("issue", IssueBookPage, "Issue Book"),
            ("return", ReturnBookPage, "Return Book"),
            ("reports", ReportsPage, "Reports"),
            ("settings", SettingsPage, "Settings"),
        ]

        for attr, page_cls, title in page_specs:
            if page_cls is not None:
                page = page_cls(self)
            else:
                page = PlaceholderPage(title)
            setattr(self, attr, page)
            self.pages.append(page)

        for page in self.pages:
            self.stack.addWidget(page)
        layout.addWidget(self.stack)
        return wrapper

    def _select_page(self, index: int):
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button:
            button.setChecked(True)
        page = self.pages[index]
        if hasattr(page, "refresh"):
            page.refresh()

    # -- Public refresh hooks -----------------------------------------------
    def navigate(self, index: int):
        self._select_page(index)

    def refresh_all(self):
        for page in self.pages:
            if hasattr(page, "refresh"):
                page.refresh()
        self._refresh_top_bar()

    def reload_after_restore(self):
        if hasattr(self.reports, "_search_students"):
            self.reports._search_students()
        self.refresh_all()
        self._select_page(0)

    def _refresh_top_bar(self):
        school = utils.get_setting("school_name", "DVNS")
        library = utils.get_setting("library_name", "School Library")
        today = utils.format_display_date(utils.today_str())
        self.top_right.setText(
            f'{school} · {library}    {today}'
        )

    def apply_updated_settings(self, settings: dict):
        school_name = settings.get("school_name", "").strip()
        library_name = settings.get("library_name", "").strip()
        due_days = int(settings.get("default_due_days", 7))
        low_stock_limit = int(settings.get("low_stock_limit", 2))

        if school_name or library_name:
            self._refresh_top_bar()

        if library_name:
            self.brand.setText(library_name)

        if hasattr(self, "dashboard"):
            self.dashboard.refresh()

        if hasattr(self, "books"):
            self.books.refresh()

        if hasattr(self, "issue") and hasattr(self.issue, "set_default_due_days"):
            self.issue.set_default_due_days(due_days)

        if hasattr(self, "reports") and hasattr(self.reports, "refresh"):
            self.reports.refresh()

        if hasattr(self, "settings"):
            self.settings.refresh()

        backup_service.set_backup_folder(settings.get("backup_path", ""))
        excel_service.set_export_folder(settings.get("export_path", ""))
