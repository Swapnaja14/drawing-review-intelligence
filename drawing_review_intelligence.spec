# -*- mode: python ; coding: utf-8 -*-
"""
drawing_review_intelligence.spec — PyInstaller bundle specification
Bundles the UCC AI Drawing Review Intelligence PySide6 desktop application into a standalone executable.
"""

import sys
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

added_files = [
    ('app/resources', 'app/resources'),
    ('docs', 'docs'),
]

hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.engine.default',
    'sqlalchemy.dialects.sqlite',
    'openpyxl',
    'PIL',
    'fitz',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UCC_Drawing_Review_Intelligence',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UCC_Drawing_Review_Intelligence',
)
