# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["../scripts/windows_launcher.py"],
    pathex=[".."],
    binaries=[],
    datas=[],
    hiddenimports=[],
    excludes=["app", "PySide6", "sqlalchemy", "litestar", "uvicorn"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="Gravewright",
    console=True,
    icon="../icon.png",
    upx=False,
)
