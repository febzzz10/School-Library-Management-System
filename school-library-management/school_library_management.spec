# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for School Library Management System (one-folder build)."""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# Data files bundled inside _internal/
# ---------------------------------------------------------------------------
datas = [
    ("assets/icons/app_icon.ico", "assets/icons"),
    ("assets/images/logo.png", "assets/images"),
    ("database/schema.sql", "database"),
    ("database/library.db", "database"),
]

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("PySide6")
hiddenimports += collect_submodules("openpyxl")

# ---------------------------------------------------------------------------
# Excludes – reduce package size by skipping unused Qt bindings
# ---------------------------------------------------------------------------
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL",
    "cv2",
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
    exclude_binaries=True,
    name="School Library Management System",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join("assets", "icons", "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="School Library Management System",
)
