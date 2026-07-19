# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for School Library Management System (one-file build).

This produces a standalone .exe that extracts to a temporary folder at
runtime.  All writable data (database, backups, exports, logs, settings)
lives in %%LOCALAPPDATA%%\\School Library Management System so that user
data survives executable replacement.
"""

import os
import site
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# Data files bundled inside the one-file archive
# ---------------------------------------------------------------------------
datas = [
    ("assets/icons/app_icon.ico", "assets/icons"),
    ("assets/images/logo.png", "assets/images"),
    ("database/schema.sql", "database"),
    ("database/library.db", "database"),
]

# Collect Qt data files (platform plugins, image formats, styles, etc.)
datas += collect_data_files("PySide6", include_py_files=False)

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("PySide6")
hiddenimports += collect_submodules("openpyxl")
hiddenimports += [
    "et_xmlfile",
    "et_xmlfile.xmlfile",
]

# ---------------------------------------------------------------------------
# Excludes – reduce package size by skipping unused bindings
# ---------------------------------------------------------------------------
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL",
    "cv2",
    "pandas",
    "numpy",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="School Library Management System",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    icon=os.path.join("assets", "icons", "app_icon.ico"),
)
