# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包規格。
打包：.\\venv\\Scripts\\python.exe -m PyInstaller laser_duel.spec --noconfirm
（禁用 pyinstaller.exe wrapper，會靜默失敗）"""

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("data", "data"),        # layouts.json / laser_table.json / puzzle_catalog.json
        ("assets", "assets"),    # 棋子/棋盤/特效/UI 圖 + sfx/*.wav
    ],
    hiddenimports=["PyQt6.QtMultimedia"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# onefile：所有東西（含 data/ 與 assets/）打包進單一 LaserDuel.exe。
# 執行時自解壓到暫存資料夾，引擎/素材以 sys._MEIPASS 定位（已支援）。
# 代價：首次啟動稍慢、防毒偶有誤判——但下載端只有一個檔案，符合需求。
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LaserDuel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # GUI app，不開 console 視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app_icon.ico",
)
