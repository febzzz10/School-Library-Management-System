"""Reusable validation functions.

Validators return a ``ValidationResult``. Services use these to reject bad
input before touching the database, and the UI shows ``result.message`` to the
user. Messages are user-friendly (no technical/database terms).
"""

from app import utils


class ValidationResult:
    """Outcome of a validation check."""

    def __init__(self, ok: bool, message: str = ""):
        self.ok = ok
        self.message = message

    def __bool__(self):
        return self.ok


def ok() -> ValidationResult:
    return ValidationResult(True, "")


def fail(message: str) -> ValidationResult:
    return ValidationResult(False, message)


# ---------------------------------------------------------------------------
# Generic field validators
# ---------------------------------------------------------------------------
def require_text(value: str, field_label: str) -> ValidationResult:
    """A required text field must be non-empty after trimming."""
    if value is None or str(value).strip() == "":
        return fail(f"{field_label} is required.")
    return ok()


def validate_quantity(value, field_label: str = "Quantity") -> ValidationResult:
    """Quantity must be a whole number that is zero or positive."""
    if value is None or str(value).strip() == "":
        return fail(f"{field_label} is required.")
    try:
        number = int(str(value).strip())
    except (ValueError, TypeError):
        return fail(f"{field_label} must be a valid number.")
    if number < 0:
        return fail(f"{field_label} cannot be negative.")
    return ok()


# ---------------------------------------------------------------------------
# Domain validators
# ---------------------------------------------------------------------------
def validate_book_form(title, total_quantity, available_quantity=None) -> ValidationResult:
    """Validate the Add/Edit book form fields."""
    check = require_text(title, "Book title")
    if not check:
        return check

    check = validate_quantity(total_quantity, "Total quantity")
    if not check:
        return check
    total = int(str(total_quantity).strip())

    if available_quantity is not None and str(available_quantity).strip() != "":
        check = validate_quantity(available_quantity, "Available quantity")
        if not check:
            return check
        available = int(str(available_quantity).strip())
        if available > total:
            return fail("Available quantity cannot be greater than total quantity.")
    return ok()


def validate_student_form(student_code, name) -> ValidationResult:
    """Validate the Add/Edit student form fields."""
    check = require_text(student_code, "Student ID")
    if not check:
        return check
    check = require_text(name, "Student name")
    if not check:
        return check
    return ok()


def validate_issue_dates(issue_date, due_date) -> ValidationResult:
    """Issue date required; due date (if given) not before issue date."""
    if not issue_date or str(issue_date).strip() == "":
        return fail("Issue date is required.")
    issue = utils.parse_date(issue_date)
    if issue is None:
        return fail("Please select a valid issue date.")
    if due_date and str(due_date).strip():
        due = utils.parse_date(due_date)
        if due is None:
            return fail("Please select a valid due date.")
        if due < issue:
            return fail("Due date cannot be earlier than issue date.")
    return ok()


def validate_return_date(issue_date, return_date) -> ValidationResult:
    """Return date required and not earlier than the issue date."""
    if not return_date or str(return_date).strip() == "":
        return fail("Please select a return date.")
    ret = utils.parse_date(return_date)
    if ret is None:
        return fail("Please select a valid return date.")
    issue = utils.parse_date(issue_date)
    if issue is not None and ret < issue:
        return fail("Return date cannot be earlier than issue date.")
    return ok()
