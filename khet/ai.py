"""對戰 AI：negamax + alpha-beta 剪枝 + 置換表 + 迭代加深。
純搜尋層（引擎之上），禁止 GUI 依賴。介面：choose_action(state, difficulty)。
"""
from __future__ import annotations

import random
import time

from khet.engine import (
    Move, Rotate, Swap, apply_action, board_map, legal_actions,
    other, resolve_laser, winner,
)

WIN = 1_000_000
# 子力價值。PHARAOH 不計（沒了就是輸，由 WIN 處理）；SCARAB 不可能被移除，
# 材料上是常數，故為 0。
PIECE_VALUE = {"PHARAOH": 0, "SPHINX": 0, "SCARAB": 0, "ANUBIS": 900, "PYRAMID": 500}
GUARD_BONUS = 40          # 法老周邊每顆己方棋的肉盾加分
THREAT_PHARAOH = 5000     # 「現在發射就能打中法老」的威脅分
_EXACT, _LOWER, _UPPER = 0, 1, 2
_TIME_CHECK_INTERVAL = 512


class _Timeout(Exception):
    pass


def evaluate(state: tuple) -> int:
    """回傳「輪到走的一方」觀點的分數（negamax 慣例）。不處理已分勝負的局面。"""
    player, pieces = state
    occ = board_map(pieces)
    score = {"RED": 0, "SILVER": 0}
    pharaohs = {}
    for p in pieces:
        score[p[1]] += PIECE_VALUE[p[0]]
        if p[0] == "PHARAOH":
            pharaohs[p[1]] = p

    # 法老安全度：周邊 8 格的己方棋數
    for color, ph in pharaohs.items():
        guard = 0
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                q = occ.get((ph[2] + dc, ph[3] + dr))
                if q is not None and q[1] == color:
                    guard += 1
        score[color] += guard * GUARD_BONUS

    # 雷射威脅：假想雙方「現在就發射」會打掉什麼（粗略但便宜的一手威脅偵測）
    for color in ("RED", "SILVER"):
        _, res = resolve_laser(pieces, color)
        if res.event == "hit":
            victim = res.hit_piece
            v = THREAT_PHARAOH if victim[0] == "PHARAOH" else PIECE_VALUE[victim[0]] // 2 + 50
            score[victim[1]] -= v

    return score[player] - score[other(player)]


def _terminal_score(state: tuple, w: str, ply: int) -> int:
    """勝負已定時，從「輪到走的一方」觀點給分；ply 越小的勝利分數越高（催促速勝）。"""
    return (WIN - ply) if w == state[0] else -(WIN - ply)


def _order_actions(actions: list, tt_best, killers: tuple = ()) -> list:
    """走法排序：置換表最佳手 → killer 手（曾引發剪枝）→ 換位/移動 → 旋轉。"""
    def key(a):
        if tt_best is not None and a == tt_best:
            return 0
        if a in killers:
            return 1
        if isinstance(a, Swap):
            return 2
        if isinstance(a, Move):
            return 3
        return 4
    return sorted(actions, key=key)


class _Searcher:
    def __init__(self, deadline: float):
        self.deadline = deadline
        self.tt: dict = {}          # state -> (depth, score, flag, best_action)
        self.killers: dict = {}     # ply -> (action, action)：該層曾引發 beta 剪枝的手
        self.nodes = 0

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes % _TIME_CHECK_INTERVAL == 0 and time.monotonic() > self.deadline:
            raise _Timeout

    def negamax(self, state: tuple, depth: int, alpha: int, beta: int, ply: int) -> int:
        self._tick()
        w = winner(state)
        if w is not None:
            return _terminal_score(state, w, ply)
        if depth == 0:
            return evaluate(state)

        alpha_orig = alpha
        entry = self.tt.get(state)
        tt_best = None
        if entry is not None:
            e_depth, e_score, e_flag, tt_best = entry
            if e_depth >= depth:
                if e_flag == _EXACT:
                    return e_score
                if e_flag == _LOWER:
                    alpha = max(alpha, e_score)
                elif e_flag == _UPPER:
                    beta = min(beta, e_score)
                if alpha >= beta:
                    return e_score

        best = -WIN * 2
        best_act = None
        killers = self.killers.get(ply, ())
        for a in _order_actions(legal_actions(state), tt_best, killers):
            child, _ = apply_action(state, a)
            val = -self.negamax(child, depth - 1, -beta, -alpha, ply + 1)
            if val > best:
                best, best_act = val, a
            alpha = max(alpha, val)
            if alpha >= beta:
                if a not in killers:            # 記住剪枝手，同層兄弟節點優先試
                    self.killers[ply] = (a,) + killers[:1]
                break

        flag = _EXACT
        if best <= alpha_orig:
            flag = _UPPER
        elif best >= beta:
            flag = _LOWER
        self.tt[state] = (depth, best, flag, best_act)
        return best


REPEAT_PENALTY = 150      # 根節點：走向「已出現過的局面」每次出現扣的分（避免和局迴圈）


def search(state: tuple, max_depth: int, time_limit: float = 3.0,
           noise: int = 0, rng: random.Random | None = None,
           history_counts: dict | None = None):
    """迭代加深搜尋，回傳 (best_action, info)。超時回傳最後完成深度的結果。
    history_counts：對局至今各 state 出現次數（三次同形偵測用的那份），
    用來在根節點降權「走回舊局面」的手。"""
    searcher = _Searcher(time.monotonic() + time_limit)
    root_actions = legal_actions(state)
    if not root_actions:
        raise RuntimeError("無合法行動（規則上不可能）")
    rng = rng or random.Random()
    rng.shuffle(root_actions)     # 打破決定性：同分手隨機挑，對局才有變化
    best_action = root_actions[0]
    completed_depth = 0
    # 上一輪各手分數 → 這一輪的根排序
    prev_scores = {a: 0 for a in root_actions}

    for depth in range(1, max_depth + 1):
        ordered = sorted(root_actions, key=lambda a: -prev_scores.get(a, 0))
        alpha, beta = -WIN * 2, WIN * 2
        scores = {}
        iter_best, iter_best_act = -WIN * 2, None
        timed_out = False
        try:
            for a in ordered:
                child, _ = apply_action(state, a)
                val = -searcher.negamax(child, depth - 1, -beta, -alpha, 1)
                if history_counts:
                    val -= REPEAT_PENALTY * history_counts.get(child, 0)
                if noise:
                    val += rng.uniform(-noise, noise)
                scores[a] = val
                if val > iter_best:
                    iter_best, iter_best_act = val, a
                alpha = max(alpha, val)
        except _Timeout:
            timed_out = True
        # 部分完成的一輪也採用目前最佳：排最前的是上輪最佳手（已重搜過），
        # 因此部分結果只會「換成更深層驗證過更好的手」，不會變差。
        if iter_best_act is not None:
            best_action = iter_best_act
        if not timed_out:
            prev_scores = scores
            completed_depth = depth
        if timed_out or iter_best >= WIN - depth - 1:   # 超時或已找到必勝
            break

    info = {"depth": completed_depth, "nodes": searcher.nodes}
    return best_action, info


# 深度分級 2/3/6 是 Python 效能實測後的決定（開局深度 4≈2s、深度 5≈20s）：
# medium 固定深度 3 秒出手快、強度穩定；hard 用時限 + 超時部分採用逐步逼近 4-5 層。
DIFFICULTIES = {
    "easy": dict(max_depth=2, time_limit=1.0, noise=250),
    "medium": dict(max_depth=3, time_limit=3.0, noise=0),
    "hard": dict(max_depth=6, time_limit=5.0, noise=0),
}


def choose_action(state: tuple, difficulty: str = "medium",
                  time_limit: float | None = None,
                  rng: random.Random | None = None,
                  history_counts: dict | None = None):
    cfg = DIFFICULTIES[difficulty]
    action, _info = search(
        state,
        max_depth=cfg["max_depth"],
        time_limit=cfg["time_limit"] if time_limit is None else time_limit,
        noise=cfg["noise"],
        rng=rng,
        history_counts=history_counts,
    )
    return action
