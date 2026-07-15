"""SQLite database backup and restore.

Backups are timestamped copies of ``library.db``. Restore always creates an
automatic safety backup of the current database first, then replaces it.
"""

import os
import shutil
import sqlite3
from datetime import datetime

from app import config, database, utils
from services import ServiceError

_backup_folder = None


def set_backup_folder(path: str):
    """Update the backup folder at runtime (overrides config.BACKUPS_DIR)."""
    global _backup_folder
    _backup_folder = path


def _timestamp_for_filename() -> str:
    """Filesystem-safe timestamp: YYYY-MM-DD_HH-MM-SS."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def backup_database(directory: str = None) -> str:
    """Copy the live database to a timestamped file in the backups folder.

    Uses SQLite's online backup API so the copy is consistent even if the app
    is mid-write. Returns the saved path.
    """
    if not os.path.exists(config.DATABASE_PATH):
        raise ServiceError("No database file found to back up.")

    target_dir = directory or _backup_folder or config.BACKUPS_DIR
    os.makedirs(target_dir, exist_ok=True)
    filename = f"library_backup_{_timestamp_for_filename()}.db"
    dest = os.path.join(target_dir, filename)

    try:
        source = sqlite3.connect(config.DATABASE_PATH)
        backup_conn = sqlite3.connect(dest)
        with backup_conn:
            source.backup(backup_conn)
        backup_conn.close()
        source.close()
    except sqlite3.Error as exc:
        raise ServiceError(
            "Backup failed. Please check folder permission."
        ) from exc

    utils.set_setting("last_backup_at", utils.now_timestamp())
    utils.log_activity("DB_BACKUP", f"Database backup created: {dest}")
    return dest


def restore_database(backup_path: str) -> str:
    """Replace the current database with a selected backup file.

    A safety backup of the current database is created first. Returns the path
    of that safety backup so the UI can mention it.
    """
    if not backup_path or not os.path.exists(backup_path):
        raise ServiceError("Selected backup file could not be found.")

    if not _looks_like_sqlite(backup_path):
        raise ServiceError("The selected file is not a valid database backup.")

    # 1) Auto-backup current database before overwriting.
    safety_path = None
    if os.path.exists(config.DATABASE_PATH):
        safety_dir = os.path.join(config.BACKUPS_DIR, "auto_before_restore")
        try:
            safety_path = backup_database(safety_dir)
        except ServiceError:
            # If even the safety backup fails, fall back to a plain file copy.
            os.makedirs(safety_dir, exist_ok=True)
            safety_path = os.path.join(
                safety_dir, f"pre_restore_{_timestamp_for_filename()}.db"
            )
            shutil.copy2(config.DATABASE_PATH, safety_path)

    # 2) Replace the live database file.
    try:
        shutil.copy2(backup_path, config.DATABASE_PATH)
    except OSError as exc:
        raise ServiceError(
            "Restore failed while replacing the database file."
        ) from exc

    # 3) Make sure the restored database has the required schema/objects.
    try:
        database.initialize_database()
    except database.DatabaseError as exc:
        raise ServiceError(
            "The backup was restored but the schema could not be verified. "
            "Try restoring again or contact support."
        ) from exc

    utils.log_activity("DB_RESTORE", f"Database restored from: {backup_path}")
    return safety_path


def list_backups(directory: str = None):
    """Return available .db backup files, newest first."""
    target_dir = directory or _backup_folder or config.BACKUPS_DIR
    if not os.path.isdir(target_dir):
        return []
    entries = []
    for name in os.listdir(target_dir):
        if name.lower().endswith(".db"):
            full = os.path.join(target_dir, name)
            entries.append((full, os.path.getmtime(full)))
    entries.sort(key=lambda item: item[1], reverse=True)
    return [path for path, _ in entries]


def last_backup_display() -> str:
    """Human-friendly last backup time, or a placeholder."""
    value = utils.get_setting("last_backup_at", "")
    if not value:
        return "No backup created yet."
    parsed = utils.parse_date(value)
    if parsed is None:
        return value
    # value is a full timestamp; show date + time.
    try:
        dt = datetime.strptime(value, utils.DATETIME_FORMAT)
        return dt.strftime("%d %B %Y, %I:%M %p")
    except ValueError:
        return value


def _looks_like_sqlite(path: str) -> bool:
    """Verify a file starts with the SQLite magic header."""
    try:
        with open(path, "rb") as handle:
            return handle.read(16).startswith(b"SQLite format 3")
    except OSError:
        return False
