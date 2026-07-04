"""雷射棋核心規則引擎（純函式層，無 GUI 依賴）。

State 表示：
    state = (current_player, pieces)
    pieces = tuple(sorted( (type, color, col, row, orientation) ))
座標/方向/朝向定義見 docs/agent_manual/01_conventions.md。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

# ---------------------------------------------------------------- 資料載入
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name: str) -> dict:
    with open(os.path.join(_ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


_LASER = _load("laser_table.json")["table"]
_LAYOUTS = _load("layouts.json")

COLS = _LAYOUTS["board"]["cols"]          # 10
ROWS = _LAYOUTS["board"]["rows"]          # 8
RESTRICTED = {
    "RED": {tuple(c) for c in _LAYOUTS["restricted"]["RED"]},
    "SILVER": {tuple(c) for c in _LAYOUTS["restricted"]["SILVER"]},
}
SPHINX_INFO = _LAYOUTS["sphinx"]           # 位置與合法朝向
FIRST_PLAYER = _LAYOUTS["first_player"]    # "SILVER"

# 方向：0=N 1=E 2=S 3=W
DIR_VECTORS = ((0, -1), (1, 0), (0, 1), (-1, 0))
# 8 方向移動（N 起順時針）
MOVE_VECTORS = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))

MAX_BEAM_STEPS = 500


def other(player: str) -> str:
    return "RED" if player == "SILVER" else "SILVER"


# ---------------------------------------------------------------- 行動型別
@dataclass(frozen=True)
class Move:
    col: int
    row: int
    dcol: int
    drow: int


@dataclass(frozen=True)
class Swap:            # 僅 SCARAB
    col: int
    row: int
    dcol: int
    drow: int


@dataclass(frozen=True)
class Rotate:
    col: int
    row: int
    cw: bool           # True=順時針


@dataclass(frozen=True)
class LaserResult:
    path: tuple        # ((col,row), ...) 光束經過的每一格（含起點 Sphinx 格）
    event: str         # "exit" | "absorb" | "hit"
    hit_piece: tuple | None   # 被移除的棋子 (type,color,col,row,ori)，無則 None


# ---------------------------------------------------------------- 基本工具
def initial_state(layout: str = "classic") -> tuple:
    pieces = tuple(sorted(
        (p["type"], p["color"], p["col"], p["row"],
         p["orientation"] % (2 if p["type"] == "SCARAB" else 4))
        for p in _LAYOUTS["layouts"][layout]
    ))
    return (FIRST_PLAYER, pieces)


def board_map(pieces: tuple) -> dict:
    """(col,row) -> piece tuple。呼叫端自行快取，引擎內部每次重建（正確性優先）。"""
    return {(p[2], p[3]): p for p in pieces}


def in_board(col: int, row: int) -> bool:
    return 0 <= col < COLS and 0 <= row < ROWS


def can_occupy(color: str, col: int, row: int) -> bool:
    """color 的棋子可否停留在 (col,row)——限制格檢查。"""
    return (col, row) not in RESTRICTED[other(color)]


# ---------------------------------------------------------------- 合法行動
def legal_actions(state: tuple) -> list:
    player, pieces = state
    occ = board_map(pieces)
    actions = []
    for p in pieces:
        ptype, color, col, row, ori = p
        if color != player:
            continue

        # 旋轉
        if ptype == "SPHINX":
            # 在 2 個合法朝向間切換（cw 值無意義，恆為 True 保持介面一致）
            actions.append(Rotate(col, row, True))
        elif ptype == "SCARAB":
            actions.append(Rotate(col, row, True))   # '\' <-> '/'，順逆等價，只給一個
        elif ptype in ("PYRAMID", "ANUBIS"):
            actions.append(Rotate(col, row, True))
            actions.append(Rotate(col, row, False))
        # PHARAOH 不給旋轉行動：官方允許但對稱無意義，刻意省略以縮小 AI 分支

        # 移動 / 換位
        if ptype == "SPHINX":
            continue
        for dcol, drow in MOVE_VECTORS:
            ncol, nrow = col + dcol, row + drow
            if not in_board(ncol, nrow):
                continue
            target = occ.get((ncol, nrow))
            if target is None:
                if can_occupy(color, ncol, nrow):
                    actions.append(Move(col, row, dcol, drow))
            elif ptype == "SCARAB" and target[0] in ("PYRAMID", "ANUBIS"):
                # 換位：scarab 要能停 target 格、target 要能停 scarab 原格
                if can_occupy(color, ncol, nrow) and can_occupy(target[1], col, row):
                    actions.append(Swap(col, row, dcol, drow))
    return actions


# ---------------------------------------------------------------- 套用行動
def _rotate_piece(piece: tuple, cw: bool) -> tuple:
    ptype, color, col, row, ori = piece
    if ptype == "SPHINX":
        legal = SPHINX_INFO[color]["legal_orientations"]
        new_ori = legal[1] if ori == legal[0] else legal[0]
    elif ptype == "SCARAB":
        new_ori = (ori + 1) % 2
    else:
        new_ori = (ori + (1 if cw else -1)) % 4
    return (ptype, color, col, row, new_ori)


def _apply_action_no_laser(state: tuple, action) -> tuple:
    player, pieces = state
    occ = board_map(pieces)
    if isinstance(action, Rotate):
        target = occ[(action.col, action.row)]
        new_pieces = [p for p in pieces if p is not target]
        new_pieces.append(_rotate_piece(target, action.cw))
    elif isinstance(action, Move):
        target = occ[(action.col, action.row)]
        new_pieces = [p for p in pieces if p is not target]
        new_pieces.append((target[0], target[1],
                           action.col + action.dcol, action.row + action.drow, target[4]))
    elif isinstance(action, Swap):
        a = occ[(action.col, action.row)]
        b = occ[(action.col + action.dcol, action.row + action.drow)]
        new_pieces = [p for p in pieces if p is not a and p is not b]
        new_pieces.append((a[0], a[1], b[2], b[3], a[4]))
        new_pieces.append((b[0], b[1], a[2], a[3], b[4]))
    else:
        raise TypeError(f"unknown action: {action!r}")
    return (player, tuple(sorted(new_pieces)))


def resolve_laser(pieces: tuple, player: str) -> tuple[tuple, LaserResult]:
    """發射 player 的雷射，回傳（結算後 pieces, LaserResult）。"""
    occ = board_map(pieces)
    info = SPHINX_INFO[player]
    sphinx = occ[(info["col"], info["row"])]
    col, row, direction = sphinx[2], sphinx[3], sphinx[4]
    path = [(col, row)]

    for _ in range(MAX_BEAM_STEPS):
        dcol, drow = DIR_VECTORS[direction]
        col, row = col + dcol, row + drow
        if not in_board(col, row):
            return pieces, LaserResult(tuple(path), "exit", None)
        path.append((col, row))
        piece = occ.get((col, row))
        if piece is None:
            continue
        outcome = _LASER[piece[0]][piece[4]][direction]
        if outcome["result"] == "reflect":
            direction = outcome["dir"]
        elif outcome["result"] == "absorb":
            return pieces, LaserResult(tuple(path), "absorb", None)
        else:  # hit
            new_pieces = tuple(sorted(p for p in pieces if p is not piece))
            return new_pieces, LaserResult(tuple(path), "hit", piece)
    raise RuntimeError("laser exceeded MAX_BEAM_STEPS（理論上不可能，資料表壞了）")


def apply_action(state: tuple, action) -> tuple[tuple, LaserResult]:
    """執行行動 + 強制雷射，回傳 (新 state, LaserResult)。不檢查行動合法性
    （呼叫端應只傳入 legal_actions 的結果）。"""
    player, _ = state
    mid_player, mid_pieces = _apply_action_no_laser(state, action)
    new_pieces, result = resolve_laser(mid_pieces, mid_player)
    return ((other(player), new_pieces), result)


# ---------------------------------------------------------------- 勝負
def winner(state: tuple) -> str | None:
    """回傳 'RED' / 'SILVER' / None。法老不在場的一方輸。"""
    _, pieces = state
    alive = {p[1] for p in pieces if p[0] == "PHARAOH"}
    if "RED" not in alive:
        return "SILVER"
    if "SILVER" not in alive:
        return "RED"
    return None
