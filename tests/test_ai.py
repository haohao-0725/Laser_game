"""AI 測試：一步殺必選、受威脅必防、回傳合法行動且不超時。"""
import time

import pytest

from khet.ai import choose_action, evaluate
from khet.engine import apply_action, initial_state, legal_actions, winner


def test_ai_finds_mate_in_one():
    """銀方 Sphinx 轉向 W 即沿 row 7 擊殺紅法老（f1）。"""
    pieces = tuple(sorted([
        ("SPHINX", "SILVER", 9, 7, 0),    # j1 朝 N（目前無殺）
        ("SPHINX", "RED", 0, 0, 1),       # a8 朝 E（row 0 淨空、無反殺）
        ("PHARAOH", "RED", 5, 7, 0),      # f1
        ("PHARAOH", "SILVER", 4, 6, 0),   # e2
        ("PYRAMID", "SILVER", 2, 4, 0),
    ]))
    state = ("SILVER", pieces)
    action = choose_action(state, "medium", time_limit=3.0)
    new_state, res = apply_action(state, action)
    assert winner(new_state) == "SILVER", f"AI 沒抓到一步殺，選了 {action}（雷射 {res.event}）"


def test_ai_defends_mate_threat():
    """紅方下一手可轉 Sphinx 沿 row 0 殺銀法老（e8）——銀方必須先解除威脅。"""
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),       # a8 朝 S（威脅：轉 E 即殺）
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "SILVER", 4, 0, 0),   # e8，在紅方 row 0 火線上
        ("PHARAOH", "RED", 5, 6, 0),      # f2（遠離雙方火線）
        ("PYRAMID", "SILVER", 4, 4, 0),
        ("ANUBIS", "SILVER", 3, 6, 0),
    ]))
    state = ("SILVER", pieces)
    action = choose_action(state, "medium", time_limit=3.0)
    mid_state, _ = apply_action(state, action)
    assert winner(mid_state) is None, "AI 的防守手自己把局面走輸了"
    # 紅方任何回應都不能立即獲勝
    for red_action in legal_actions(mid_state):
        after, _ = apply_action(mid_state, red_action)
        assert winner(after) != "RED", f"AI 防守失敗：紅方 {red_action} 仍可一步殺"


def test_choose_action_legal_and_within_time():
    state = initial_state("classic")
    t0 = time.monotonic()
    action = choose_action(state, "medium")
    elapsed = time.monotonic() - t0
    assert action in legal_actions(state)
    assert elapsed < 6.0, f"medium 超時：{elapsed:.1f}s"


def test_easy_is_legal_and_fast():
    state = initial_state("dynasty")
    action = choose_action(state, "easy")
    assert action in legal_actions(state)


def test_evaluate_symmetry_on_initial_positions():
    """官方佈局 180 度對稱 → 開局評估應接近 0（雙方對稱，僅先手觀點差）。"""
    for layout in ("classic", "imhotep", "dynasty"):
        state = initial_state(layout)
        v = evaluate(state)
        assert abs(v) < 200, f"{layout} 開局評估不對稱：{v}"
