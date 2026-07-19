# School Library Management System

An offline desktop application for managing school library operations. Built with Python, PySide6, and SQLite.

## Features

- **Dashboard** — Overview of library statistics (total books, available, issued, students, pending returns, overdue, low stock)
- **Books Management** — Add, edit, deactivate, search, filter, import/export books via Excel
- **Student Management** — Add, edit, deactivate, search, import/export students via Excel, view issue history
- **Issue Book** — Issue books to students with automatic quantity updates, duplicate prevention
- **Return Book** — Record returns, overdue tracking, automatic quantity recovery
- **Reports** — 10 report types with search, date filters, and Excel export
- **Settings** — School/library configuration, SQLite backup/restore, Excel full backup

## Download (No Python required)

Download the standalone executable from the [Releases](https://github.com/febzzz10/School-Library-Management-System/releases) page:

| File | Description |
|---|---|
| `School Library Management System.exe` | Single-file standalone. Copy anywhere and run. No Python or DLLs needed. |
| `School-Library-Management-System-Setup.exe` | Installer (recommended for most users) |

Data is stored in `%LOCALAPPDATA%\School Library Management System\` and persists across updates.

## Requirements (for development)

- Python 3.10+
- PySide6
- openpyxl

## Installation (for development)

```bash
pip install -r requirements.txt
```

## Usage (from source)

```bash
python main.py
```

## Build a standalone executable

See [BUILD.md](BUILD.md) for detailed build instructions, including one-folder, one-file, and Inno Setup installer builds.

### Quick build

```bash
build_exe.bat
```

Output: `dist\School Library Management System\`

## Project Structure

```
school-library-management/
├── main.py              # Application entry point
├── app/                 # Core: config, database, validators, utils
├── services/            # Business logic: books, students, issues, reports, excel, backup
├── ui/                  # PySide6 UI: main window, dashboard, all screens
├── database/            # SQLite schema and database file
├── exports/             # Exported Excel reports
├── backups/             # Database backups
├── assets/              # Icons and images
├── installer/           # Inno Setup installer output
├── installer.iss        # Inno Setup script
├── build_exe.bat        # PyInstaller build script
├── pyproject.toml       # Project metadata and test config
├── README.md            # This file
├── BUILD.md             # Build instructions
└── AGENTS.md            # AI agent instructions
```

## Tech Stack

- **UI:** PySide6 (Qt6)
- **Database:** SQLite
- **Excel:** openpyxl
- **Packaging:** PyInstaller (one-file & one-folder builds), Inno Setup (installer)
- **Testing:** pytest

## License

MIT
