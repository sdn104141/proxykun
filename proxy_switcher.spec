# -*- mode: python ; coding: utf-8 -*-


import os, sys
# customtkinter のデータファイルパスを自動取得
try:
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    ctk_data = [(ctk_path, 'customtkinter')]
except ImportError:
    ctk_data = []

a = Analysis(
    ['proxy_switcher.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')] + ctk_data,
    hiddenimports=['customtkinter'],
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
    name='proxy_switcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowe