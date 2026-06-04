# Warframe Relic Tracker - PyInstaller Spec File
# Build with: pyinstaller installer/warframe-relic-tracker.spec

import os

a = Analysis(
    ['../src/main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../src/static', 'src/static'),
    ],
    hiddenimports=[
        'src.db.models',
        'src.db.database',
        'src.config',
        'src.api.relics',
        'src.api.overview',
        'src.api.collection',
        'src.services.sync',
        'src.services.collection',
        'src.services.market_api',
        'src.services.drop_data',
        'src.services.ducats',
        'aiosqlite',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RelicTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
