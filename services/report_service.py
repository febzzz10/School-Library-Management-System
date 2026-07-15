"""Reporting logic: dashboard summary and all report data queries.

Each ``report_*`` function returns a tuple ``(columns, rows)`` where columns is
a list of header strings and rows is a list of dicts. The UI renders these
generically and the Excel service exports them the same way.
"""

import logging

from app import database, utils
from services import ServiceError, issue_service, student_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def dashboard_summary() -> dict:
    """Return all headline numbers for the dashboard cards."""
    try:
        low_limit = utils.get_setting_int("low_stock_limit", 2)
        return {
            "total_books": int(database.fetch_value(
                "SELECT COALESCE(SUM(total_quantity), 0) FROM books WHERE status = 'ACTIVE'",
                default=0)),
            "available_books": int(database.fetch_value(
                "SELECT COALESCE(SUM(available_quantity), 0) FROM books WHERE status = 'ACTIVE'",
                default=0)),
            "issued_books": int(database.fetch_value(
                "SELECT COUNT(*) FROM book_issues WHERE status = 'ISSUED'", default=0)),
            "total_students": int(database.fetch_value(
                "SELECT COUNT(*) FROM students WHERE status = 'ACTIVE'", default=0)),
            "pending_returns": int(database.fetch_value(
                "SELECT COUNT(*) FROM book_issues WHERE status = 'ISSUED'", default=0)),
            "overdue_books": int(database.fetch_value(
                "SELECT COUNT(*) FROM book_issues WHERE status = 'ISSUED' "
                "AND due_date IS NOT NULL AND date(due_date) < date('now')", default=0)),
            "low_stock_books": int(database.fetch_value(
                "SELECT COUNT(*) FROM books WHERE status = 'ACTIVE' "
                "AND available_quantity <= ?", (low_limit,), default=0)),
        }
    except database.DatabaseError:
        logger.exception("dashboard_summary failed")
        return {}


def recent_issues(limit: int = 8):
    """Most recent issue records for the dashboard."""
    try:
        query = (
            "SELECT s.name AS student_name, b.title AS book_title, bi.issue_date, "
            "bi.due_date, bi.status FROM book_issues bi "
            "JOIN books b ON bi.book_id = b.id "
            "JOIN students s ON bi.student_id = s.id "
            "ORDER BY bi.id DESC LIMIT ?"
        )
        return [dict(r) for r in database.fetch_all(query, (limit,))]
    except database.DatabaseError:
        logger.exception("recent_issues failed")
        return []


def recent_returns(limit: int = 8):
    """Most recent return records for the dashboard."""
    try:
        query = (
            "SELECT s.name AS student_name, b.title AS book_title, bi.issue_date, "
            "bi.return_date FROM book_issues bi "
            "JOIN books b ON bi.book_id = b.id "
            "JOIN students s ON bi.student_id = s.id "
            "WHERE bi.status = 'RETURNED' AND bi.return_date IS NOT NULL "
            "ORDER BY bi.return_date DESC, bi.id DESC LIMIT ?"
        )
        return [dict(r) for r in database.fetch_all(query, (limit,))]
    except database.DatabaseError:
        logger.exception("recent_returns failed")
        return []


# ---------------------------------------------------------------------------
# Reports — each returns (columns, rows)
# ---------------------------------------------------------------------------
def report_all_books(search: str = ""):
    try:
        like = f"%{search.strip()}%" if search else "%"
        rows = database.fetch_all(
            "SELECT id, title, author, category, "
            "total_quantity, available_quantity, status FROM books "
            "WHERE (title LIKE ? OR author LIKE ? OR category LIKE ?) "
            "ORDER BY title ASC",
            (like, like, like),
        )
        columns = ["ID", "Title", "Author", "Category",
                   "Total Qty", "Available Qty", "Status"]
        return columns, [dict(r) for r in rows]
    except database.DatabaseError:
        logger.exception("report_all_books failed")
        raise ServiceError("Unable to load book report.")


def report_available_books(search: str = ""):
    try:
        like = f"%{search.strip()}%" if search else "%"
        rows = database.fetch_all(
            "SELECT id, title, author, category, available_quantity "
            "FROM books WHERE status = 'ACTIVE' AND available_quantity > 0 "
            "AND (title LIKE ? OR author LIKE ? OR category LIKE ?) ORDER BY title ASC",
            (like, like, like),
        )
        columns = ["ID", "Title", "Author", "Category", "Available Qty"]
        return columns, [dict(r) for r in rows]
    except database.DatabaseError:
        logger.exception("report_available_books failed")
        raise ServiceError("Unable to load available books report.")


def report_low_stock(search: str = ""):
    try:
        limit = utils.get_setting_int("low_stock_limit", 2)
        like = f"%{search.strip()}%" if search else "%"
        rows = database.fetch_all(
            "SELECT id, title, author, category, total_quantity, available_quantity "
            "FROM books WHERE status = 'ACTIVE' AND available_quantity <= ? "
            "AND (title LIKE ? OR author LIKE ?) ORDER BY available_quantity ASC",
            (limit, like, like),
        )
        columns = ["ID", "Title", "Author", "Category", "Total Qty", "Available Qty"]
        return columns, [dict(r) for r in rows]
    except database.DatabaseError:
        logger.exception("report_low_stock failed")
        raise ServiceError("Unable to load low stock report.")


def report_students(search: str = ""):
    try:
        like = f"%{search.strip()}%" if search else "%"
        rows = database.fetch_all(
            "SELECT student_code, name, class_name, division, status "
            "FROM students WHERE (student_code LIKE ? OR name LIKE ? OR class_name LIKE ?) "
            "ORDER BY name ASC",
            (like, like, like),
        )
        rows = [dict(r) for r in rows]
        for row in rows:
            if row.get("division"):
                row["division"] = row["division"].strip().upper()
        columns = ["Student ID", "Name", "Class", "Division", "Status"]
        return columns, rows
    except database.DatabaseError:
        logger.exception("report_students failed")
        raise ServiceError("Unable to load student report.")


def report_issued_books(search: str = "", date_from: str = None, date_to: str = None):
    return _issue_report(status="ISSUED", search=search,
                         date_from=date_from, date_to=date_to)


def report_returned_books(search: str = "", date_from: str = None, date_to: str = None):
    return _issue_report(status="RETURNED", search=search,
                         date_from=date_from, date_to=date_to)


def report_pending_returns(search: str = ""):
    columns = ["Issue ID", "Student ID", "Student Name", "Book Title",
               "Issue Date", "Due Date", "Overdue Days"]
    rows = issue_service.get_pending_returns(search)
    result = []
    for r in rows:
        result.append({
            "issue_id": r["issue_id"],
            "student_code": r.get("student_code", ""),
            "student_name": r.get("student_name", ""),
            "book_title": r.get("book_title", ""),
            "issue_date": r.get("issue_date", ""),
            "due_date": r.get("due_date", ""),
            "overdue_days": r.get("overdue_days", 0),
        })
    return columns, result


def report_overdue(search: str = ""):
    columns = ["Issue ID", "Student ID", "Student Name", "Book Title",
               "Issue Date", "Due Date", "Overdue Days"]
    rows = issue_service.get_overdue_books(search)
    return columns, rows


def report_student_history(student_id: int):
    columns = ["Issue ID", "Book Title", "Issue Date", "Due Date",
               "Return Date", "Status"]
    rows = student_service.get_student_history(student_id)
    return columns, rows


def report_date_wise_issue(date_from: str = None, date_to: str = None):
    return _date_report("issue_date", date_from, date_to)


def report_date_wise_return(date_from: str = None, date_to: str = None):
    return _date_report("return_date", date_from, date_to, only_returned=True)


# ---------------------------------------------------------------------------
# Internal shared builders
# ---------------------------------------------------------------------------
def _issue_report(status, search="", date_from=None, date_to=None):
    try:
        like = f"%{search.strip()}%" if search else "%"
        clauses = ["bi.status = ?",
                   "(s.student_code LIKE ? OR s.name LIKE ? OR b.title LIKE ?)"]
        params = [status, like, like, like]
        if date_from:
            clauses.append("date(bi.issue_date) >= date(?)")
            params.append(date_from)
        if date_to:
            clauses.append("date(bi.issue_date) <= date(?)")
            params.append(date_to)
        where = " AND ".join(clauses)
        rows = database.fetch_all(
            f"SELECT bi.id AS issue_id, s.student_code, s.name AS student_name, "
            f"b.title AS book_title, bi.issue_date, bi.due_date, bi.return_date, "
            f"bi.status FROM book_issues bi JOIN books b ON bi.book_id = b.id "
            f"JOIN students s ON bi.student_id = s.id WHERE {where} "
            f"ORDER BY bi.issue_date DESC, bi.id DESC",
            tuple(params),
        )
        columns = ["Issue ID", "Student ID", "Student Name", "Book Title",
                   "Issue Date", "Due Date", "Return Date", "Status"]
        return columns, [dict(r) for r in rows]
    except database.DatabaseError:
        logger.exception("_issue_report failed")
        raise ServiceError("Unable to load the requested report.")


def _date_report(date_field, date_from, date_to, only_returned=False):
    try:
        clauses = [f"bi.{date_field} IS NOT NULL"]
        params = []
        if only_returned:
            clauses.append("bi.status = 'RETURNED'")
        if date_from:
            clauses.append(f"date(bi.{date_field}) >= date(?)")
            params.append(date_from)
        if date_to:
            clauses.append(f"date(bi.{date_field}) <= date(?)")
            params.append(date_to)
        where = " AND ".join(clauses)
        rows = database.fetch_all(
            f"SELECT bi.id AS issue_id, s.student_code, s.name AS student_name, "
            f"b.title AS book_title, bi.issue_date, bi.due_date, bi.return_date, "
            f"bi.status FROM book_issues bi JOIN books b ON bi.book_id = b.id "
            f"JOIN students s ON bi.student_id = s.id WHERE {where} "
            f"ORDER BY bi.{date_field} DESC, bi.id DESC",
            tuple(params),
        )
        columns = ["Issue ID", "Student ID", "Student Name", "Book Title",
                   "Issue Date", "Due Date", "Return Date", "Status"]
        return columns, [dict(r) for r in rows]
    except database.DatabaseError:
        logger.exception("_date_report failed")
        raise ServiceError("Unable to load the requested report.")
