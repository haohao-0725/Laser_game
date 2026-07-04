"""引擎行為測試。黃金向量來自查證過的 classic 開局光束路徑（agent_manual 03 章 §7）。"""
import pytest

from khet.engine import (
    Move, Swap, Rotate, initial_state, legal_actions, apply_action,
    resolve_laser, winner, board_map, RESTRICTED,
)


def piece_at(state, col, row):
    return board_map(state[1]).get((col, row))


# ---------- 黃金向量：classic 開局光束（查證於官方 Laser Chess 資料）----------
def test_classic_silver_opening_beam():
    """銀方雷射：j1 → 上行 → j4 反射 W → h4 反射 N → h5 反射 E → j5 反射 N → 出界。"""
    _, pieces = initial_state("classic")
    new_pieces, res = resolve_laser(pieces, "SILVER")
    assert res.event == "exit"
    assert new_pieces == pieces           # 無棋被移除
    for cell in [(9, 7), (9, 4), (7, 4), (7, 3), (9, 3)]:   # 必經轉折格
        assert cell in res.path


def test_classic_red_opening_beam():
    """紅方雷射：a8 → 下行 → a5 反射 E → c5 反射 S → c4 反射 W → a4 反射 S → 出界。"""
    _, pieces = initial_state("classic")
    _, res = resolve_laser(pieces, "RED")
    assert res.event == "exit"
    for cell in [(0, 0), (0, 3), (2, 3), (2, 4), (0, 4)]:
        assert cell in res.path


# ---------- 初始局面 ----------
@pytest.mark.parametrize("layout", ["classic", "imhotep", "dynasty"])
def test_initial_state_sane(layout):
    state = initial_state(layout)
    assert state[0] == "SILVER"           # 銀方先手
    assert len(state[1]) == 26
    assert winner(state) is None
    assert len(legal_actions(state)) > 0
    # 開局光束（雙方）都不打死任何棋：官方佈局的已知性質
    for color in ("RED", "SILVER"):
        _, res = resolve_laser(state[1], color)
        assert res.event == "exit"


# ---------- 基礎規則 ----------
def test_sphinx_cannot_move_and_rotates_between_two_orientations():
    state = initial_state("classic")
    sphinx_actions = [a for a in legal_actions(state) if (a.col, a.row) == (9, 7)]
    assert sphinx_actions and all(isinstance(a, Rotate) for a in sphinx_actions)
    new_state, _ = apply_action(state, sphinx_actions[0])
    assert piece_at(new_state, 9, 7)[4] == 3      # N(0) -> W(3)
    # 再轉一次要轉回來（紅方回合先跳過：直接對 pieces 驗證旋轉函式由 fuzz 覆蓋）


def test_restricted_squares_block_moves():
    """銀方棋子不可移入紅方限制格（a 欄 / i8 / i1）。"""
    state = initial_state("classic")
    for a in legal_actions(state):
        if isinstance(a, (Move, Swap)):
            dst = (a.col + a.dcol, a.row + a.drow)
            assert dst not in RESTRICTED["RED"], f"{a} 移入紅方限制格"


def test_scarab_swap_targets_only_pyramid_or_anubis():
    state = initial_state("classic")
    occ = board_map(state[1])
    silver_swaps = [a for a in legal_actions(state) if isinstance(a, Swap)]
    assert silver_swaps, "classic 開局銀方應至少有一個換位（f4 scarab ↔ g3 紅 pyramid）"
    for a in silver_swaps:
        target = occ[(a.col + a.dcol, a.row + a.drow)]
        assert target[0] in ("PYRAMID", "ANUBIS")


def test_scarab_swap_preserves_orientations():
    """換位後兩顆棋朝向不變、位置互換。"""
    state = initial_state("classic")
    occ = board_map(state[1])
    swap = next(a for a in legal_actions(state) if isinstance(a, Swap))
    scarab = occ[(swap.col, swap.row)]
    target = occ[(swap.col + swap.dcol, swap.row + swap.drow)]
    new_state, _ = apply_action(state, swap)
    moved_scarab = piece_at(new_state, target[2], target[3])
    moved_target = piece_at(new_state, scarab[2], scarab[3])
    # 目標棋可能在換位後的強制雷射中被打掉，故 moved_target 允許為 None
    assert moved_scarab[0] == "SCARAB" and moved_scarab[4] == scarab[4]
    if moved_target is not None:
        assert moved_target[0] == target[0] and moved_target[4] == target[4]


def test_pharaoh_hit_ends_game():
    """人工局面：紅 Sphinx 直射銀 PHARAOH。"""
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),       # a8 朝 S
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "RED", 5, 0, 0),
        ("PHARAOH", "SILVER", 0, 5, 0),   # a3，在紅雷射線上（人工局面不管限制格）
    ]))
    new_pieces, res = resolve_laser(pieces, "RED")
    assert res.event == "hit" and res.hit_piece[0] == "PHARAOH"
    assert winner(("RED", new_pieces)) == "RED"


def test_self_hit_is_possible():
    """己方雷射可以打掉自己的棋（核心策略元素）。"""
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "RED", 5, 0, 0),
        ("PHARAOH", "SILVER", 4, 7, 0),
        ("PYRAMID", "RED", 0, 4, 2),      # a4 鏡面 {S,W}，弱點朝 N ——會被自家雷射打掉
    ]))
    _, res = resolve_laser(pieces, "RED")
    assert res.event == "hit" and res.hit_piece[1] == "RED"


def test_anubis_front_absorbs():
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "RED", 5, 0, 0),
        ("PHARAOH", "SILVER", 4, 7, 0),
        ("ANUBIS", "SILVER", 0, 5, 0),    # 盾朝 N，紅光從北打來 = 正面
    ]))
    new_pieces, res = resolve_laser(pieces, "RED")
    assert res.event == "absorb"
    assert new_pieces == pieces


def test_pharaoh_has_no_rotate_action():
    """刻意決策（手冊 04 章）：PHARAOH 不提供旋轉行動。"""
    state = initial_state("classic")
    occ = board_map(state[1])
    for a in legal_actions(state):
        if isinstance(a, Rotate):
            assert occ[(a.col, a.row)][0] != "PHARAOH"
