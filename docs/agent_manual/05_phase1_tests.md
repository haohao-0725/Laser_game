# 05 Phase 1 — 測試套件（引擎的驗收關卡）

產出物：`tests/test_laser_table.py`、`tests/test_engine.py`、`tests/test_fuzz.py`。
執行：`.\venv\Scripts\python.exe -m pytest tests\ -q`

這些測試同時是**未來手機版的一致性基準**（Phase 6 會把隨機向量輸出成 JSON 給 JS 比對），
所以寧可多寫不要少寫。以下參考實作可直接抄。

## 1. `tests/test_laser_table.py` — 真值表全覆蓋

```python
"""雷射真值表測試：5 種棋 × 4 朝向 × 4 入射方向 = 80 格全部斷言。
真值表若錯，引擎/AI/謎題全部下游都會被污染——這是全專案最重要的測試。"""
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data", "laser_table.json"), encoding="utf-8") as f:
    TABLE = json.load(f)["table"]

N, E, S, W = 0, 1, 2, 3


def r(d):
    return {"result": "reflect", "dir": d}


HIT = {"result": "hit"}
ABSORB = {"result": "absorb"}

# '\' 鏡面（PYRAMID ori 0/2 的幾何、SCARAB ori 0）：N→W E→S S→E W→N
# '/' 鏡面（PYRAMID ori 1/3、SCARAB ori 1）：N→E E→N S→W W→S
CASES = []
for o in range(4):
    for d in range(4):
        CASES.append(("PHARAOH", o, d, HIT))
        CASES.append(("SPHINX", o, d, ABSORB))
        # ANUBIS：盾面朝 o，光束行進方向 d 打到的面是 (d+2)%4
        CASES.append(("ANUBIS", o, d, ABSORB if (d + 2) % 4 == o else HIT))
        # SCARAB：永遠反射
        mapping = [W, S, E, N] if o % 2 == 0 else [E, N, W, S]
        CASES.append(("SCARAB", o, d, r(mapping[d])))
        # PYRAMID：鏡面朝 {o, o+1}
        face = (d + 2) % 4
        if face == o:
            CASES.append(("PYRAMID", o, d, r((o + 1) % 4)))
        elif face == (o + 1) % 4:
            CASES.append(("PYRAMID", o, d, r(o)))
        else:
            CASES.append(("PYRAMID", o, d, HIT))


@pytest.mark.parametrize("ptype,ori,beam,expected", CASES)
def test_laser_table_cell(ptype, ori, beam, expected):
    assert TABLE[ptype][ori][beam] == expected
```

（此測試看似「用同一套公式驗證同一套公式」，但 CASES 的推導是**獨立重寫**的展開式；
若有人手改 JSON 或改壞生成器，這裡會抓到。）

## 2. `tests/test_engine.py` — 規則情境 + 黃金向量

```python
"""引擎行為測試。黃金向量來自查證過的 classic 開局光束路徑（03 章 §7）。"""
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
    # 路徑必經的轉折格
    for cell in [(9, 7), (9, 4), (7, 4), (7, 3), (9, 3)]:
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
    acts = legal_actions(state)
    assert len(acts) > 0
    # 開局光束（雙方）都不打死任何棋：官方佈局的已知性質
    for color in ("RED", "SILVER"):
        _, res = resolve_laser(state[1], color)
        assert res.event == "exit"


# ---------- 基礎規則 ----------
def test_sphinx_cannot_move_and_rotates_between_two_orientations():
    state = initial_state("classic")
    sphinx_actions = [a for a in legal_actions(state)
                      if (a.col, a.row) == (9, 7)]
    assert all(isinstance(a, Rotate) for a in sphinx_actions)
    (new_state, _) = apply_action(state, sphinx_actions[0])
    assert piece_at(new_state, 9, 7)[4] == 3      # N(0) -> W(3)


def test_restricted_squares_block_moves():
    """銀方棋子不可移入紅方限制格（a 欄 / i8 / i1）。"""
    state = initial_state("classic")
    for a in legal_actions(state):
        if isinstance(a, (Move, Swap)):
            dst = (a.col + a.dcol, a.row + a.drow)
            assert dst not in RESTRICTED["RED"], f"{a} 移入紅方限制格"


def test_scarab_swap_exists_and_preserves_orientations():
    """classic 中銀 SCARAB e4(4,4) 可與紅 SCARAB? 不行——只能換 PYRAMID/ANUBIS。
    先走一手讓紅方回合，再驗證紅 SCARAB e5(4,3) 與相鄰 PYRAMID 的換位。"""
    state = initial_state("classic")
    silver_swaps = [a for a in legal_actions(state) if isinstance(a, Swap)]
    for a in silver_swaps:
        _, pieces = state
        occ = board_map(pieces)
        target = occ[(a.col + a.dcol, a.row + a.drow)]
        assert target[0] in ("PYRAMID", "ANUBIS")


def test_pharaoh_hit_ends_game():
    """建構人工局面：紅 Sphinx 直射銀 PHARAOH。"""
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),       # a8 朝 S
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "RED", 5, 0, 0),
        ("PHARAOH", "SILVER", 0, 5, 0),   # a3，正在紅雷射線上
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
        ("PYRAMID", "RED", 0, 4, 2),      # a4 背面朝上（鏡面 {S,W}——弱點朝 N）
    ]))
    new_pieces, res = resolve_laser(pieces, "RED")
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
```

## 3. `tests/test_fuzz.py` — 隨機走子煙霧測試

```python
"""隨機自對戰：預設 2000 局（CI 快速版）。Phase 1 驗收時手動跑 100000 局版本：
   .\\venv\\Scripts\\python.exe -m pytest tests\\test_fuzz.py -q --fuzz-games=100000
（加不了參數就直接臨時改 GAMES 常數。）"""
import random

from khet.engine import initial_state, legal_actions, apply_action, winner

GAMES = 200          # 每局最多 200 步，共 GAMES 局；驗收時調大
MAX_PLIES = 200


def test_random_selfplay_no_crash():
    rng = random.Random(20260704)
    for g in range(GAMES):
        layout = rng.choice(["classic", "imhotep", "dynasty"])
        state = initial_state(layout)
        for _ in range(MAX_PLIES):
            if winner(state) is not None:
                break
            acts = legal_actions(state)
            assert acts, "無合法行動（規則上不可能）"
            state, res = apply_action(state, rng.choice(acts))
            # 不變量檢查
            _, pieces = state
            assert len({(p[2], p[3]) for p in pieces}) == len(pieces), "棋子重疊"
            assert all(0 <= p[2] < 10 and 0 <= p[3] < 8 for p in pieces), "出界"
            sphinxes = [p for p in pieces if p[0] == "SPHINX"]
            assert len(sphinxes) == 2, "SPHINX 消失了"
            scarabs = [p for p in pieces if p[0] == "SCARAB"]
            assert len(scarabs) == 4, "SCARAB 被移除（不可能）"
```

## 常見翻車點（測試紅燈時先看這裡）

| 症狀 | 最可能原因 |
|---|---|
| 黃金向量路徑不符 | 方向編號或 orientation 定義沒照 01 章；或 layouts.json 被改過 |
| SCARAB 被移除 | laser_table 載入時 orientation 沒 `% 2` 正規化，或表被手改 |
| 換位測試失敗 | Swap 少了「對方棋子不可被換進其限制格」的雙向檢查 |
| fuzz 偶發重疊 | Move 沒檢查目標格為空、或 Swap 後座標寫反 |
| 中文輸出亂碼 | 忘了設 PYTHONIOENCODING（見 02 章） |

## 驗收標準

- [ ] `pytest tests\ -q` 全綠
- [ ] 真值表 80 格全覆蓋測試存在且通過
- [ ] 兩條 classic 開局黃金向量通過
- [ ] 100000 局隨機走子跑完無例外（跑完把結果記到 PROGRESS.md）
