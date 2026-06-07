# MyApp.spec
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py', 'database.py', 'inference_engine.py'],  
    pathex=[],
    binaries=[],
    datas=[], 
    hiddenimports=[
        'tkinter', 
        'uuid', 
        'sqlite3', 
        'json', 
        'datetime',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog'
    ],
    hookspath=[],
    hooksconfig={},
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
    name='MyApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False - без окна консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)