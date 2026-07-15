"""Student business logic: add, edit, deactivate, search, issue history."""

from app import config, database, utils, validators
from services import ServiceError


def get_students(search: str = "", status: str = None, class_name: str = None,
                 division: str = None):
    """Return students matching the search text and filters."""
    clauses = []
    params = []

    if search and search.strip():
        like = f"%{search.strip()}%"
        clauses.append(
            "(student_code LIKE ? OR name LIKE ? OR class_name LIKE ? "
            "OR division LIKE ?)"
        )
        params.extend([like, like, like, like])

    if status in (config.STATUS_ACTIVE, config.STATUS_INACTIVE):
        clauses.append("status = ?")
        params.append(status)

    if class_name:
        clauses.append("class_name = ?")
        params.append(class_name)

    if division:
        clauses.append("division = ?")
        params.append(division)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT * FROM students {where} ORDER BY name ASC"
    return [_upper_division(dict(r)) for r in database.fetch_all(query, tuple(params))]


def get_student(student_id: int):
    return _upper_division(
        utils.row_to_dict(
            database.fetch_one("SELECT * FROM students WHERE id = ?", (student_id,))
        )
    )


def get_active_students(search: str = ""):
    """Active students matching the search text (for the Issue screen)."""
    like = f"%{search.strip()}%" if search else "%"
    query = (
        "SELECT * FROM students WHERE status = 'ACTIVE' AND "
        "(student_code LIKE ? OR name LIKE ? OR class_name LIKE ? "
        "OR division LIKE ?) ORDER BY name ASC"
    )
    return [_upper_division(dict(r)) for r in database.fetch_all(query, (like, like, like, like))]


def add_student(data: dict) -> int:
    """Validate and insert a new student. Returns new student id."""
    code = (data.get("student_code") or "").strip()
    name = (data.get("name") or "").strip()

    result = validators.validate_student_form(code, name)
    if not result:
        raise ServiceError(result.message)

    if _code_exists(code):
        raise ServiceError("A student with this Student ID already exists.")

    division = (data.get("division") or "").strip().upper() or None

    now = utils.now_timestamp()
    try:
        student_id = database.execute(
            "INSERT INTO students (student_code, name, class_name, division, "
            "status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                code,
                name,
                (data.get("class_name") or "").strip() or None,
                division,
                data.get("status") or config.STATUS_ACTIVE,
                now,
                now,
            ),
        )
    except database.DatabaseError as exc:
        raise ServiceError(_friendly_db_error(exc)) from exc

    utils.log_activity("STUDENT_ADDED", f"Student added: {name} ({code})")
    return student_id


def update_student(student_id: int, data: dict) -> None:
    """Validate and update an existing student."""
    student = get_student(student_id)
    if student is None:
        raise ServiceError("Student not found.")

    code = (data.get("student_code") or "").strip()
    name = (data.get("name") or "").strip()
    result = validators.validate_student_form(code, name)
    if not result:
        raise ServiceError(result.message)

    if _code_exists(code, exclude_id=student_id):
        raise ServiceError("Another student with this Student ID already exists.")

    division = (data.get("division") or "").strip().upper() or None

    try:
        database.execute(
            "UPDATE students SET student_code = ?, name = ?, class_name = ?, "
            "division = ?, status = ?, "
            "updated_at = ? WHERE id = ?",
            (
                code,
                name,
                (data.get("class_name") or "").strip() or None,
                division,
                data.get("status") or student["status"],
                utils.now_timestamp(),
                student_id,
            ),
        )
    except database.DatabaseError as exc:
        raise ServiceError(_friendly_db_error(exc)) from exc

    utils.log_activity("STUDENT_UPDATED", f"Student updated: {name} ({code})")


def delete_student(student_id: int) -> None:
    """Permanently delete a student and all their history.

    Refused if the student has any currently ISSUED books.
    All operations run inside a single transaction.
    """
    student = get_student(student_id)
    if student is None:
        raise ServiceError("Student not found.")
    if get_pending_count(student_id) > 0:
        raise ServiceError(
            "This student cannot be deleted because they still have one or "
            "more books issued. Return all books before deleting the student."
        )
    try:
        with database.transaction() as conn:
            conn.execute(
                "DELETE FROM book_issues WHERE student_id = ?", (student_id,)
            )
            conn.execute(
                "DELETE FROM students WHERE id = ?", (student_id,)
            )
    except database.DatabaseError as exc:
        raise ServiceError(_friendly_db_error(exc)) from exc

    utils.log_activity(
        "STUDENT_DELETED",
        f"Student deleted: {student['name']} ({student['student_code']})",
    )


def get_pending_count(student_id: int) -> int:
    """Number of books this student currently has out."""
    return int(
        database.fetch_value(
            "SELECT COUNT(*) FROM book_issues WHERE student_id = ? AND status = 'ISSUED'",
            (student_id,),
            default=0,
        )
    )


def get_student_history(student_id: int):
    """Full issue/return history for one student, newest first."""
    query = (
        "SELECT bi.id AS issue_id, b.title AS book_title, bi.issue_date, "
        "bi.due_date, bi.return_date, bi.status "
        "FROM book_issues bi JOIN books b ON bi.book_id = b.id "
        "WHERE bi.student_id = ? ORDER BY bi.issue_date DESC, bi.id DESC"
    )
    return [dict(r) for r in database.fetch_all(query, (student_id,))]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _code_exists(code: str, exclude_id: int = None) -> bool:
    if exclude_id:
        row = database.fetch_one(
            "SELECT id FROM students WHERE student_code = ? AND id != ?",
            (code, exclude_id),
        )
    else:
        row = database.fetch_one(
            "SELECT id FROM students WHERE student_code = ?", (code,)
        )
    return row is not None


def _friendly_db_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "unique" in text and "student_code" in text:
        return "A student with this Student ID already exists."
    return "Unable to save the student. Please try again."


def _upper_division(student):
    """Uppercase division in a student dict (or None)."""
    if student is not None and student.get("division"):
        student["division"] = student["division"].strip().upper()
    return student
