# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata
import platform

hiddenimports = []
if platform.system() == "Linux":
    name="ticket-Linux"
    hiddenimports = ["plyer.platforms.linux.notification"]
elif platform.system() == "Windows":
    name="ticket-Windows"
    hiddenimports = ["plyer.platforms.win.notification"]
elif platform.system() == "Darwin":
    name="ticket-MacOS"
    hiddenimports = ["plyer.platforms.macosx.notification"]

datas = [("assest", "assest")]
datas += [("geetest", "geetest")]
datas += collect_data_files("fake_useragent")
datas += copy_metadata("readchar")


a = Analysis(
    ["cli.py"],
    pathex=[],
    binaries=[],
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
    a.binaries,
    a.datas,
    [],
    name=name,
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
    icon=["assest\\icon.ico"],
)
