# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

datas = [
    ('static', 'static'),
    ('models', 'models'),
    ('services', 'services'),
    ('utils', 'utils'),
    ('.env.example', '.'),
]
if Path('playwright-browsers').exists():
    datas.append(('playwright-browsers', 'playwright-browsers'))
binaries = []
hiddenimports = [
    'flask',
    'flask_cors',
    'openpyxl',
    'lxml',
    'pypdf',
    'requests',
    'brazilfiscalreport',
    'docling',
    'docling.document_converter',
    'playwright',
    'playwright.sync_api',
    'tkinter',
    'PIL',
]

for package_name in (
    'docling',
    'docling_core',
    'docling_parse',
    'docling_ibm_models',
    'playwright',
    'pyee',
    'rapidocr',
):
    tmp_ret = collect_all(package_name)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]


a = Analysis(
    ['main_standalone.py'],
    pathex=[],
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
    name='UltraDanfeXML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UltraDanfeXML',
)
