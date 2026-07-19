@echo off
REM ============================================================================
REM  One-file build script for School Library Management System
REM
REM  Produces a standalone executable that can be copied by itself to the
REM  Desktop or another Windows computer without the _internal folder.
REM ============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo =============================================
echo  One-File Standalone Executable Build
echo =============================================
echo.

REM ------------------------------------------------------------------
REM  0. Activate virtual environment if present
REM ------------------------------------------------------------------
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ".venv\Scripts\activate.bat"
    if errorlevel 1 (
        echo [WARNING] Virtual environment activation failed.
        echo.
    )
)

REM ------------------------------------------------------------------
REM  1. Kill any running instance of the app
REM ------------------------------------------------------------------
taskkill /f /im "School Library Management System.exe" 2>nul
echo.

REM ------------------------------------------------------------------
REM  2. Clean previous one-file build artefacts
REM ------------------------------------------------------------------
if exist "build-onefile" (
    echo Removing old build-onefile folder...
    rmdir /s /q "build-onefile"
)
if exist "dist-onefile" (
    echo Removing old dist-onefile folder...
    rmdir /s /q "dist-onefile"
)

REM Remove Python cache files
for /d /r %%d in (__pycache__) do @if exist "%%d" (
    rmdir /s /q "%%d" 2>nul
)
del /s /q *.pyc 2>nul
echo Cleaned __pycache__ and .pyc files.
echo.

REM ------------------------------------------------------------------
REM  3. Install / verify PyInstaller
REM ------------------------------------------------------------------
echo Installing / upgrading PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------------
REM  4. Build one-file executable
REM ------------------------------------------------------------------
echo Building one-file standalone executable...
echo  (This will take a few minutes...)
echo.
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --distpath dist-onefile ^
  --workpath build-onefile ^
  school_library_management_onefile.spec

if errorlevel 1 (
    echo.
    echo [ERROR] One-file build failed.
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------------
REM  5. Verify the standalone executable exists
REM ------------------------------------------------------------------
set "EXE_PATH=dist-onefile\School Library Management System.exe"

if not exist "!EXE_PATH!" (
    echo.
    echo [ERROR] Standalone executable was not created.
    echo   Expected: !EXE_PATH!
    pause
    exit /b 1
)

REM ------------------------------------------------------------------
REM  6. Summary
REM ------------------------------------------------------------------
echo =============================================
echo  One-file build completed successfully!
echo =============================================
echo.

for %%f in ("!EXE_PATH!") do (
    echo Path: !EXE_PATH!
    echo Size: %%~zf bytes  (%%~zf)
    echo Modified: %%~tf
)

echo.
echo IMPORTANT: This executable is fully standalone.
echo You can copy this single file to your Desktop
echo or to another Windows computer and run it.
echo.
echo All writable data (database, backups, exports,
echo logs, settings) is stored in:
echo   %%LOCALAPPDATA%%\School Library Management System\
echo.
echo Existing data in the original one-folder build
echo (dist\) is NOT affected.
echo.

pause
endlocal
