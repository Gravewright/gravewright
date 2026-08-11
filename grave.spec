# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('schemas', 'schemas'),
    ('migrations', 'migrations'),
    ('alembic.ini', '.'),
    (
        'app/engine/sdk/capabilities.json',
        'app/engine/sdk',
    ),
    (
        'data/packages/rulesets/gravewright-pdf-system',
        'bundled-packages/rulesets/gravewright-pdf-system',
    ),
]

binaries = []
hiddenimports = []


# Gravewright / server
tmp_ret = collect_all('litestar')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('uvicorn')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('websockets')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

hiddenimports += [
    'uvicorn.protocols.websockets.websockets_sansio_impl',
]

tmp_ret = collect_all('httptools')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

tmp_ret = collect_all('app')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


# Desktop UI is provided by PySide6. PyInstaller's official Qt hook follows the
# imported QtCore/QtGui/QtWidgets modules and collects their required plugins.


a = Analysis(
    ['desktop.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Gravewright',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],
)


exe_debug = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Gravewright-debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],
)


coll = COLLECT(
    exe,
    exe_debug,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Gravewright',
)
