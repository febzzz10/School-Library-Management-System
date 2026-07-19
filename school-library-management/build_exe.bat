@echo off
REM ============================================================================
REM  Build script for School Library Management System
REM ============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo =============================================
echo  Building School Library Management System
echo =============================================
echo.

REM ------------------------------------------------------------------
REM  0. Kill any running instance of the app
REM ------------------------------------------------------------------
taskkill /f /im "School Library Management System.exe" 2>nul
echo.

REM ------------------------------------------------------------------
REM  1. Clean previous build artefacts
REM ------------------------------------------------------------------
if exist "build" (
    echo Removing old build folder...
    rmdir /s /q "build"
)
if exist "dist" (
    echo Removing old dist folder...
    rmdir /s /q "dist"
)

REM Remove Python cache files
for /d /r %%d in (__pycache__) do @if exist "%%d" (
    rmdir /s /q "%%d" 2>nul
)
del /s /q *.pyc 2>nul
echo Cleaned __pycache__ and .pyc files.
echo.

REM ------------------------------------------------------------------
REM  2. Install / verify PyInstaller
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
REM  3. Build
REM ------------------------------------------------------------------
echo Running PyInstaller...
python -m PyInstaller --noconfirm --clean school_library_management.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------------
REM  4. Verify required runtime files
REM ------------------------------------------------------------------
set "INTERNAL_DIR=dist\School Library Management System\_internal"
set "PYTHON_DLL=!INTERNAL_DIR!\python314.dll"

if not exist "!PYTHON_DLL!" (
    echo.
    echo [ERROR] Build incomplete — missing runtime DLL:
    echo   !PYTHON_DLL!
    echo.
    pause
    exit /b 1
)
echo [OK] Runtime DLL found: python314.dll
echo.

REM ------------------------------------------------------------------
REM  5. Build installer if Inno Setup is available
REM ------------------------------------------------------------------
set "ISCC="
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Inno Setup 6\ISCC.exe"

if defined ISCC (
    echo Building installer...
    "%ISCC%" installer.iss
    if errorlevel 1 (
        echo [WARNING] Installer build failed.
    ) else (
        echo [OK] Installer built.
    )
) else (
    echo.
    echo [SKIP] Inno Setup not found. Install Inno Setup 6 from
    echo        https://jrsoftware.org/isdl.php to build the installer.
    echo        After installing, re-run this script.
    echo.
)

REM ------------------------------------------------------------------
REM  6. Summary
REM ------------------------------------------------------------------
echo =============================================
echo  Build completed successfully!
echo =============================================
echo.
set "EXE_PATH=dist\School Library Management System\School Library Management System.exe"
if exist "!EXE_PATH!" (
    echo Executable: !EXE_PATH!
    for %%f in ("!EXE_PATH!") do (
        echo Date modified: %%~tf
        echo Size: %%~zf bytes
    )
) else (
    echo [WARNING] Expected executable not found at:
    echo   !EXE_PATH!
)
echo.
echo IMPORTANT: Do not move or copy only the EXE file.
echo The _internal folder must stay beside the executable.
echo.
echo To run from the Desktop, use a shortcut that targets:
echo   !EXE_PATH!
echo.
echo Or copy the complete folder:
echo   dist\School Library Management System\
echo.
pause
endlocal
