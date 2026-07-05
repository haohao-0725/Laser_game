"""謎題目錄載入與每日一題挑選。無 Qt 依賴。"""
import json
import os
import sys
from datetime import date

from khet.engine import pieces_from_list

ROOT = getattr(sys, "_MEIPASS",
               os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG_PATH = os.path.join(ROOT, "data", "puzzle_catalog.json")

DIFFICULTY_NAMES = {1: "入門（1 手）", 2: "中等（2 手）", 3: "困難（3 手）"}


def load_catalog() -> list:
    """回傳 puzzle dict 列表，附上 state 供直接開局。缺檔回空列表。"""
    if not os.path.exists(CATALOG_PATH):
        return []
    with open(CATALOG_PATH, encoding="utf-8") as f:
        cat = json.load(f)
    puzzles = cat.get("puzzles", [])
    for p in puzzles:
        p["state"] = (p["player"], pieces_from_list(p["pieces"]))
    return puzzles


def daily_puzzle(puzzles: list):
    """依日期挑一題，全球同步、不需伺服器。空目錄回 None。"""
    if not puzzles:
        return None
    ordered = sorted(puzzles, key=lambda p: p["id"])
    return ordered[date.today().toordinal() % len(ordered)]
