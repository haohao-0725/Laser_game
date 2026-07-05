"""素材載入與快取。原則（AGENT.md）：檔案存在就用圖、不存在就回 None，
由 board_widget 畫幾何佔位圖形 fallback，兩者可隨時切換。"""
import os
import sys

from PyQt6.QtGui import QPixmap

ROOT = getattr(sys, "_MEIPASS",
               os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(ROOT, "assets")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")

# (type, color) -> 檔名（docs/asset_generation_guide.md §7 檔名總表）
PIECE_FILES = {
    ("PHARAOH", "SILVER"): "silver_king.png",
    ("PHARAOH", "RED"): "red_king.png",
    ("SPHINX", "SILVER"): "silver_emitter.png",
    ("SPHINX", "RED"): "red_emitter.png",
    ("PYRAMID", "SILVER"): "silver_mirror.png",
    ("PYRAMID", "RED"): "red_mirror.png",
    ("SCARAB", "SILVER"): "silver_twinmirror.png",
    ("SCARAB", "RED"): "red_twinmirror.png",
    ("ANUBIS", "SILVER"): "silver_shield.png",
    ("ANUBIS", "RED"): "red_shield.png",
}
# 素材基準方向 = orientation 0（已逐張目視驗證：鏡面 NW-SE、盾/砲口朝上），
# 繪製時旋轉 orientation * 90 度即可。


class AssetStore:
    """QPixmap 快取。必須在 QApplication 建立後才能使用。"""

    def __init__(self) -> None:
        self._cache: dict[str, QPixmap | None] = {}

    def image(self, filename: str) -> QPixmap | None:
        if filename not in self._cache:
            path = os.path.join(ASSETS_DIR, filename)
            pm = QPixmap(path) if os.path.exists(path) else QPixmap()
            self._cache[filename] = None if pm.isNull() else pm
        return self._cache[filename]

    def piece(self, ptype: str, color: str) -> QPixmap | None:
        return self.image(PIECE_FILES[(ptype, color)])


_store: AssetStore | None = None


def store() -> AssetStore:
    global _store
    if _store is None:
        _store = AssetStore()
    return _store


sound_enabled = True                 # 由設定選單切換（main_window 持久化）
_effects: dict = {}


def play_sound(name: str) -> None:
    """播放音效（assets/sfx/<name>.wav，由 scripts/gen_sfx.py 生成）。
    QtMultimedia 不可用或檔案不存在時靜默略過。"""
    if not sound_enabled:
        return
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QSoundEffect
    except ImportError:
        return
    path = os.path.join(SFX_DIR, f"{name}.wav")
    if not os.path.exists(path):
        return
    if name not in _effects:
        eff = QSoundEffect()
        eff.setSource(QUrl.fromLocalFile(path))
        eff.setVolume(0.5)
        _effects[name] = eff
    _effects[name].play()
