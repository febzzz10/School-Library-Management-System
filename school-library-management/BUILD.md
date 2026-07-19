# Building the Executable

## Prerequisites

- Python 3.10+
- PySide6, openpyxl (installed via `pip install -r requirements.txt`)
- PyInstaller (installed automatically by the build script)
- (Optional) Inno Setup 6+ for the installer — download from [jrsoftware.org](https://jrsoftware.org/isdl.php)

## Quick Build (One-Folder)

Double-click `build_exe.bat` or run it from a terminal:

```
build_exe.bat
```

The script will:

1. Remove any previous `build`/`dist` folders
2. Install/upgrade PyInstaller
3. Build using `school_library_management.spec`
4. Print the final executable path

## Manual Build

```
pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean school_library_management.spec
```

## Output

After a successful build the executable is at:

```
dist\School Library Management System\School Library Management System.exe
```

This is a **one-folder** build. The entire `dist\School Library Management System\`
folder can be copied to another computer (even one without Python) and the
`.exe` can be launched by double-clicking.

> **IMPORTANT:** Do not copy or distribute only the `.exe` file.
> The executable requires the `_internal\` folder beside it.
> Always copy the complete `School Library Management System\` folder
> or create a **shortcut** to the original executable.

## Building the Installer (Inno Setup)

After running `build_exe.bat`, build the installer:

1. Open `installer.iss` in Inno Setup
2. Click **Build** → **Compile**
3. The installer is created at `installer\SchoolLibraryManagement_Setup_1.0.0.exe`

Or compile from the command line:

```
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

The installer:

- Installs to `%LOCALAPPDATA%\Programs\School Library Management System\`
- Creates a Desktop shortcut
- Adds Start Menu entries
- Preserves existing data on reinstall (database, backups, exports, logs)

## Single-File Build (Experimental)

For a standalone `.exe` that does not need a `_internal` folder, run:

```
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "School Library Management System" ^
  --icon "assets\icons\app_icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "database\schema.sql;database" ^
  --add-data "database\library.db;database" ^
  --hidden-import "PySide6" --hidden-import "openpyxl" ^
  main.py
```

The one-file build is **larger** and **slightly slower to start** (it extracts
`_internal` to a temporary folder on every launch). The default one-folder build
is recommended for daily use.

Output: `dist-onefile\School Library Management System.exe`

## Data Storage

- **Database, backups, exports** are stored in:
  `%LOCALAPPDATA%\School Library Management System\`

- **Logs** are stored in:
  `%LOCALAPPDATA%\School Library Management System\logs\`

These are persistent — they survive reinstalling or rebuilding the executable.

## Rebuilding

If you modify the source code, re-run `build_exe.bat` to regenerate
the executable with your changes. Existing database data is not affected.
Then recompile `installer.iss` in Inno Setup to produce an updated installer.
