"""謎題求解器測試。"""
from khet.engine import apply_action, initial_state, winner
from khet.puzzles import best_defense, forced_win_in


def _mate_in_one_state():
    """銀方轉 Sphinx 朝 W 即沿 row 7 殺紅法老（同 test_ai 的局面）。"""
    pieces = tuple(sorted([
        ("SPHINX", "SILVER", 9, 7, 0),
        ("SPHINX", "RED", 0, 0, 1),
        ("PHARAOH", "RED", 5, 7, 0),
        ("PHARAOH", "SILVER", 4, 6, 0),
        ("PYRAMID", "SILVER", 2, 4, 0),
    ]))
    return ("SILVER", pieces)


def test_solver_finds_mate_in_one():
    state = _mate_in_one_state()
    action = forced_win_in(state, "SILVER", 1)
    assert action is not None
    new_state, _ = apply_action(state, action)
    assert winner(new_state) == "SILVER"


def test_solver_rejects_impossible_mate():
    """開局不可能 1 手殺。"""
    state = initial_state("classic")
    assert forced_win_in(state, "SILVER", 1) is None


def test_exactly_n_semantics():
    """一步殺局面：n=1 有解 → 不是「恰好 2 步」謎題（生成器據此分級）。"""
    state = _mate_in_one_state()
    assert forced_win_in(state, "SILVER", 1) is not None
    assert forced_win_in(state, "SILVER", 2) is not None   # n 遞增單調：1 步能贏 2 步也能


def test_best_defense_refutes_when_possible():
    """紅方受威脅（銀方下一手轉 Sphinx 殺 f1 法老）——輪紅方走，
    best_defense 應找到破解手（把法老移出 row 7 火線）。"""
    pieces = tuple(sorted([
        ("SPHINX", "SILVER", 9, 7, 0),     # 朝 N；威脅：轉 W 掃 row 7
        ("SPHINX", "RED", 0, 0, 1),
        ("PHARAOH", "RED", 5, 7, 0),       # f1，在火線上
        ("PHARAOH", "SILVER", 4, 5, 0),
        ("PYRAMID", "RED", 2, 2, 0),
    ]))
    state = ("RED", pieces)
    action = best_defense(state, "SILVER", 1)
    mid, _ = apply_action(state, action)
    # 防守後銀方不能 1 手殺
    assert forced_win_in(mid, "SILVER", 1) is None
