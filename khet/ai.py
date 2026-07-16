"""桌面對戰 AI v2：可重複局面感知的 PVS/alpha-beta 搜尋。"""
from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
import random
import time

from khet.engine import (
    MOVE_VECTORS, Move, Rotate, Swap, apply_action, board_map, can_occupy,
    in_board, legal_actions, other, resolve_laser, winner,
)

WIN = 1_000_000
DRAW = 0
MATE_THRESHOLD = WIN - 10_000
INF = WIN * 2

PIECE_VALUE = {
    "PHARAOH": 0,
    "SPHINX": 0,
    "SCARAB": 0,
    "ANUBIS": 900,
    "PYRAMID": 500,
}
GUARD_BONUS = 40
PHARAOH_ESCAPE_BONUS = 8
SCARAB_SWAP_BONUS = 4
BEAM_REFLECTION_BONUS = 2
BEAM_PRESSURE_BONUS = 12
BEAM_NEAR_PHARAOH = 60
SELF_HIT_PENALTY = 300
THREAT_PHARAOH = 5_000
ABSORB_PRESSURE = 20

_EXACT, _LOWER, _UPPER = 0, 1, 2
_TIME_CHECK_INTERVAL = 128
_ASPIRATION = 350
_Q_DEPTH = 1
_Q_MAX_MOVES = 12
_ROOT_REPEAT_PENALTY = 120
_TT_MAX = 250_000
_ACTION_CACHE_MAX = 512
_REP_MASK = (1 << 64) - 1


class _Timeout(Exception):
    pass


def _chebyshev_to_path(cell: tuple[int, int], path: tuple) -> int:
    if not path:
        return 99
    return min(max(abs(cell[0] - col), abs(cell[1] - row)) for col, row in path)


@lru_cache(maxsize=50_000)
def _position_scores(pieces: tuple) -> tuple[int, int, bool]:
    """一次整理雙方靜態特徵；相同 pieces 換手時可直接重用。"""
    occ = board_map(pieces)
    scores = {"RED": 0, "SILVER": 0}
    pharaohs = {}
    for piece in pieces:
        scores[piece[1]] += PIECE_VALUE[piece[0]]
        if piece[0] == "PHARAOH":
            pharaohs[piece[1]] = piece

    scarab_swaps = {"RED": 0, "SILVER": 0}
    pharaoh_escapes = {"RED": 0, "SILVER": 0}
    for piece in pieces:
        ptype, color, col, row, _ = piece
        if ptype not in ("PHARAOH", "SCARAB"):
            continue
        for dcol, drow in MOVE_VECTORS:
            ncol, nrow = col + dcol, row + drow
            if not in_board(ncol, nrow):
                continue
            target = occ.get((ncol, nrow))
            if target is None and can_occupy(color, ncol, nrow):
                if ptype == "PHARAOH":
                    pharaoh_escapes[color] += 1
            elif (ptype == "SCARAB" and target is not None
                  and target[0] in ("PYRAMID", "ANUBIS")
                  and can_occupy(color, ncol, nrow)
                  and can_occupy(target[1], col, row)):
                scarab_swaps[color] += 1

    for color, pharaoh in pharaohs.items():
        scores[color] += scarab_swaps[color] * SCARAB_SWAP_BONUS
        scores[color] += pharaoh_escapes[color] * PHARAOH_ESCAPE_BONUS
        guard = 0
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                neighbour = occ.get((pharaoh[2] + dc, pharaoh[3] + dr))
                if neighbour is not None and neighbour[1] == color:
                    guard += 1
        scores[color] += guard * GUARD_BONUS

    volatile = False
    for color in ("RED", "SILVER"):
        enemy = other(color)
        _, result = resolve_laser(pieces, color)
        path = result.path[1:]
        reflections = sum(
            1 for cell in path[:-1]
            if (cell in occ and occ[cell][0] in ("PYRAMID", "SCARAB"))
        )
        scores[color] += reflections * BEAM_REFLECTION_BONUS

        enemy_pharaoh = pharaohs.get(enemy)
        if enemy_pharaoh is not None:
            distance = _chebyshev_to_path((enemy_pharaoh[2], enemy_pharaoh[3]), path)
            scores[enemy] -= max(0, 8 - distance) * BEAM_PRESSURE_BONUS
            if distance <= 2:
                scores[enemy] -= (3 - distance) * BEAM_NEAR_PHARAOH
            if distance <= 1:
                volatile = True

        if result.event == "hit":
            volatile = True
            victim = result.hit_piece
            value = (THREAT_PHARAOH if victim[0] == "PHARAOH"
                     else PIECE_VALUE[victim[0]] // 2 + 50)
            scores[victim[1]] -= value
            if victim[1] == color:
                scores[color] -= SELF_HIT_PENALTY
        elif result.event == "absorb" and result.path:
            blocker = occ.get(result.path[-1])
            if blocker is not None and blocker[1] == enemy:
                scores[enemy] -= ABSORB_PRESSURE

    return scores["RED"], scores["SILVER"], volatile


def evaluate(state: tuple) -> int:
    """回傳輪到走的一方觀點的靜態分數；終局由搜尋器先處理。"""
    player, pieces = state
    red, silver, _ = _position_scores(pieces)
    return (red - silver) if player == "RED" else (silver - red)


def _terminal_score(state: tuple, victor: str, ply: int) -> int:
    return (WIN - ply) if victor == state[0] else -(WIN - ply)


def _score_to_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score


def _score_from_tt(score: int, ply: int) -> int:
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score


@lru_cache(maxsize=250_000)
def _repetition_token(state: tuple, count: int) -> int:
    return hash((state, count, 0x4B484554)) & _REP_MASK


def _history_hash(counts: dict) -> int:
    value = 0
    for state, count in counts.items():
        if count >= 2:
            value ^= _repetition_token(state, count)
    return value


class _Searcher:
    def __init__(self, deadline: float):
        self.deadline = deadline
        # repetition hash 也是 key 的一部分，避免不同歷史錯用同一 TT 分數。
        self.tt: dict = {}
        self.killers: dict = {}
        self.history: dict = {}
        # 只快取合法行動；子局面必須等走法真的被搜尋時才結算，才能讓剪枝省工。
        self.action_cache: OrderedDict = OrderedDict()
        self.eval_cache: dict = {}
        self.nodes = 0
        self.qnodes = 0
        self.tt_hits = 0
        self.cutoffs = 0

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes % _TIME_CHECK_INTERVAL == 0 and time.monotonic() > self.deadline:
            raise _Timeout

    def _check_time(self) -> None:
        if time.monotonic() > self.deadline:
            raise _Timeout

    def _evaluate(self, state: tuple) -> int:
        score = self.eval_cache.get(state)
        if score is None:
            score = evaluate(state)
            if len(self.eval_cache) >= 50_000:
                self.eval_cache.clear()
            self.eval_cache[state] = score
        return score

    def actions(self, state: tuple) -> tuple:
        cached = self.action_cache.get(state)
        if cached is not None:
            self.action_cache.move_to_end(state)
            return cached
        result = tuple(legal_actions(state))
        self.action_cache[state] = result
        if len(self.action_cache) > _ACTION_CACHE_MAX:
            self.action_cache.popitem(last=False)
        return result

    def forcing_entries(self, state: tuple) -> tuple:
        """只結算確實可能改變目前光路的行動，避免 qsearch 重展開全部分支。"""
        player, pieces = state
        occ = board_map(pieces)
        _, current_laser = resolve_laser(pieces, player)
        beam_cells = set(current_laser.path)
        must_evade_self_hit = (
            current_laser.event == "hit"
            and current_laser.hit_piece[1] == player
        )
        candidates = []
        unchanged_representative = None
        for action in legal_actions(state):
            source = (action.col, action.row)
            target = source
            if isinstance(action, (Move, Swap)):
                target = (action.col + action.dcol, action.row + action.drow)
            piece = occ[source]
            affects_beam = (
                piece[0] == "SPHINX"
                or source in beam_cells
                or target in beam_cells
            )
            if affects_beam:
                candidates.append(action)
            elif current_laser.event == "hit" and unchanged_representative is None:
                # 光路原本已會吃子；其餘不碰光路的手在 qsearch 中等價，留一手即可。
                unchanged_representative = action
        if unchanged_representative is not None:
            candidates.append(unchanged_representative)

        forcing = []
        for index, action in enumerate(candidates):
            if index % 12 == 0:
                self._check_time()
            child, laser = apply_action(state, action)
            evades_self_hit = (
                must_evade_self_hit
                and not (laser.event == "hit" and laser.hit_piece[1] == player)
            )
            if laser.event == "hit" or winner(child) is not None or evades_self_hit:
                forcing.append((action, child, laser))
        return tuple(forcing)

    def _order_actions(self, state: tuple, actions: tuple, tt_best, ply: int) -> list:
        player = state[0]
        killers = self.killers.get(ply, ())
        _, laser = resolve_laser(state[1], player)
        beam_cells = set(laser.path)

        def priority(action):
            score = self.history.get((player, action), 0)
            if action == tt_best:
                score += 4_000_000_000
            if action in killers:
                score += 3_000_000_000

            source = (action.col, action.row)
            target = source
            if isinstance(action, (Move, Swap)):
                target = (action.col + action.dcol, action.row + action.drow)
            changes_beam = source in beam_cells or target in beam_cells
            if laser.event == "hit" and not changes_beam:
                victim = laser.hit_piece
                value = PIECE_VALUE[victim[0]] + 100
                score += (2_000_000_000 + value if victim[1] != player
                          else -2_000_000_000 - value)
            elif changes_beam:
                score += 1_000_000
            if isinstance(action, Swap):
                score += 300
            elif isinstance(action, Move):
                score += 200
            elif isinstance(action, Rotate):
                score += 100
            return score

        return sorted(actions, key=priority, reverse=True)

    def _order_entries(self, state: tuple, entries: tuple, tt_best, ply: int) -> list:
        """已結算的少量戰術走法仍以實際殺王／吃子結果排序。"""
        player = state[0]

        def priority(entry):
            action, child, laser = entry
            if winner(child) == player:
                return 4_000_000_000
            if laser.event == "hit":
                victim = laser.hit_piece
                value = PIECE_VALUE[victim[0]] + 100
                return (3_000_000_000 + value if victim[1] != player
                        else -1_000_000_000 - value)
            return self.history.get((player, action), 0)

        return sorted(entries, key=priority, reverse=True)

    def _descend(self, child: tuple, laser, callback, counts: dict, rep_hash: int):
        # 吃子後棋子數單調減少，先前局面再也不可能重現，可安全重置循環歷史。
        if laser.event == "hit":
            child_counts = {child: 1}
            return callback(child_counts, 0)

        old_count = counts.get(child, 0)
        if old_count >= 2:
            rep_hash ^= _repetition_token(child, old_count)
        new_count = old_count + 1
        counts[child] = new_count
        if new_count >= 2:
            rep_hash ^= _repetition_token(child, new_count)
        try:
            return callback(counts, rep_hash)
        finally:
            if old_count:
                counts[child] = old_count
            else:
                counts.pop(child, None)

    def _store_tt(self, key, depth: int, score: int, flag: int, action, ply: int) -> None:
        if len(self.tt) >= _TT_MAX and key not in self.tt:
            self.tt.pop(next(iter(self.tt)))
        self.tt[key] = (depth, _score_to_tt(score, ply), flag, action)

    def negamax(self, state: tuple, depth: int, alpha: int, beta: int, ply: int,
                counts: dict, rep_hash: int) -> int:
        self._tick()
        victor = winner(state)
        if victor is not None:
            return _terminal_score(state, victor, ply)
        if counts.get(state, 0) >= 3:
            return DRAW
        if depth <= 0:
            if _position_scores(state[1])[2]:
                return self.qsearch(state, alpha, beta, ply, _Q_DEPTH, counts, rep_hash)
            return self._evaluate(state)

        alpha_orig, beta_orig = alpha, beta
        key = (state, rep_hash)
        entry = self.tt.get(key)
        tt_best = None
        if entry is not None:
            entry_depth, stored_score, flag, tt_best = entry
            score = _score_from_tt(stored_score, ply)
            if entry_depth >= depth:
                self.tt_hits += 1
                if flag == _EXACT:
                    return score
                if flag == _LOWER:
                    alpha = max(alpha, score)
                else:
                    beta = min(beta, score)
                if alpha >= beta:
                    return score

        best = -INF
        best_action = None
        ordered = self._order_actions(state, self.actions(state), tt_best, ply)
        for index, action in enumerate(ordered):
            child, laser = apply_action(state, action)
            def full(child_counts, child_hash):
                return -self.negamax(
                    child, depth - 1, -beta, -alpha, ply + 1,
                    child_counts, child_hash,
                )

            if index == 0:
                value = self._descend(child, laser, full, counts, rep_hash)
            else:
                def scout(child_counts, child_hash):
                    return -self.negamax(
                        child, depth - 1, -alpha - 1, -alpha, ply + 1,
                        child_counts, child_hash,
                    )
                value = self._descend(child, laser, scout, counts, rep_hash)
                if alpha < value < beta:
                    value = self._descend(child, laser, full, counts, rep_hash)

            if value > best:
                best, best_action = value, action
            if value > alpha:
                alpha = value
            if alpha >= beta:
                self.cutoffs += 1
                killers = self.killers.get(ply, ())
                if action not in killers:
                    self.killers[ply] = (action,) + killers[:1]
                key_h = (state[0], action)
                self.history[key_h] = self.history.get(key_h, 0) + depth * depth
                break

        flag = _EXACT
        if best <= alpha_orig:
            flag = _UPPER
        elif best >= beta_orig:
            flag = _LOWER
        self._store_tt(key, depth, best, flag, best_action, ply)
        return best

    def qsearch(self, state: tuple, alpha: int, beta: int, ply: int, qdepth: int,
                counts: dict, rep_hash: int) -> int:
        self.qnodes += 1
        self._check_time()
        victor = winner(state)
        if victor is not None:
            return _terminal_score(state, victor, ply)
        if counts.get(state, 0) >= 3:
            return DRAW

        stand_pat = self._evaluate(state)
        _, current_laser = resolve_laser(state[1], state[0])
        must_evade_self_hit = (
            current_laser.event == "hit"
            and current_laser.hit_piece[1] == state[0]
        )
        if qdepth <= 0:
            return stand_pat
        if not must_evade_self_hit and stand_pat >= beta:
            return stand_pat
        if not must_evade_self_hit and stand_pat > alpha:
            alpha = stand_pat

        forcing = self.forcing_entries(state)
        if not forcing:
            return stand_pat

        best = -INF if must_evade_self_hit else stand_pat
        for action, child, laser in self._order_entries(state, forcing, None, ply)[:_Q_MAX_MOVES]:
            def descend(child_counts, child_hash):
                return -self.qsearch(
                    child, -beta, -alpha, ply + 1, qdepth - 1,
                    child_counts, child_hash,
                )
            value = self._descend(child, laser, descend, counts, rep_hash)
            if value > best:
                best = value
            if value > alpha:
                alpha = value
            if alpha >= beta:
                self.cutoffs += 1
                break
        return best


def _prepare_history(state: tuple, history_counts: dict | None) -> dict:
    material = len(state[1])
    counts = {
        old_state: count
        for old_state, count in (history_counts or {}).items()
        if count > 0 and len(old_state[1]) == material
    }
    counts[state] = max(1, counts.get(state, 0))
    return counts


def _search_root(searcher: _Searcher, state: tuple, depth: int,
                 alpha: int, beta: int, entries: list,
                 counts: dict, rep_hash: int):
    scores = {}
    best_score, best_action = -INF, None
    timed_out = False
    root_alpha = alpha
    try:
        for index, (action, child, laser) in enumerate(entries):
            def full(child_counts, child_hash):
                return -searcher.negamax(
                    child, depth - 1, -beta, -root_alpha, 1,
                    child_counts, child_hash,
                )

            if index == 0:
                value = searcher._descend(child, laser, full, counts, rep_hash)
            else:
                def scout(child_counts, child_hash):
                    return -searcher.negamax(
                        child, depth - 1, -root_alpha - 1, -root_alpha, 1,
                        child_counts, child_hash,
                    )
                value = searcher._descend(child, laser, scout, counts, rep_hash)
                if root_alpha < value < beta:
                    value = searcher._descend(child, laser, full, counts, rep_hash)

            # 第二次走回舊局面尚未正式和局，但在均勢時通常只是浪費先手。
            # 第三次同形仍由 negamax 精確回傳 DRAW，不在此改寫。
            if counts.get(child, 0) == 1 and abs(value) < MATE_THRESHOLD:
                value -= _ROOT_REPEAT_PENALTY

            scores[action] = value
            if value > best_score:
                best_score, best_action = value, action
            if value > root_alpha:
                root_alpha = value
            if root_alpha >= beta:
                searcher.cutoffs += 1
                break
    except _Timeout:
        timed_out = True
    return best_score, best_action, scores, timed_out


def search(state: tuple, max_depth: int, time_limit: float = 3.0,
           noise: int = 0, rng: random.Random | None = None,
           history_counts: dict | None = None):
    """迭代加深 PVS；三次同形在整棵搜尋樹中直接視為 0 分終局。"""
    counts = _prepare_history(state, history_counts)
    if counts.get(state, 0) >= 3:
        raise RuntimeError("目前局面已因三次同形判和")

    searcher = _Searcher(time.monotonic() + time_limit)
    root_entries = []
    for action in searcher.actions(state):
        child, laser = apply_action(state, action)
        root_entries.append((action, child, laser))
    if not root_entries:
        raise RuntimeError("無合法行動（規則上不可能）")
    rng = rng or random.Random()
    rng.shuffle(root_entries)

    rep_hash = _history_hash(counts)
    best_action = root_entries[0][0]
    best_score = 0
    completed_depth = 0
    completed_scores = {}
    prev_scores = {}

    target_depth = max_depth
    if max_depth >= 3:
        if len(state[1]) <= 10:
            target_depth += 2
        elif len(state[1]) <= 16:
            target_depth += 1

    for depth in range(1, target_depth + 1):
        ordered = sorted(
            root_entries,
            key=lambda entry: -prev_scores.get(entry[0], 0),
        )
        if completed_depth:
            alpha, beta = best_score - _ASPIRATION, best_score + _ASPIRATION
        else:
            alpha, beta = -INF, INF

        score, action, scores, timed_out = _search_root(
            searcher, state, depth, alpha, beta, ordered, counts, rep_hash,
        )
        if action is not None:
            best_action = action
        if timed_out:
            break

        if score <= alpha or score >= beta:
            score, action, scores, timed_out = _search_root(
                searcher, state, depth, -INF, INF, ordered, counts, rep_hash,
            )
            if action is not None:
                best_action = action
            if timed_out:
                break

        best_score = score
        prev_scores = scores
        completed_scores = scores
        completed_depth = depth
        if noise and scores:
            best_action = max(
                scores,
                key=lambda candidate: scores[candidate] + rng.uniform(-noise, noise),
            )
        elif action is not None:
            best_action = action
        if best_score >= WIN - depth - 1:
            break

    info = {
        "depth": completed_depth,
        "score": best_score,
        "nodes": searcher.nodes,
        "qnodes": searcher.qnodes,
        "tt_hits": searcher.tt_hits,
        "cutoffs": searcher.cutoffs,
        "root_scores": completed_scores,
        "target_depth": target_depth,
    }
    return best_action, info


DIFFICULTIES = {
    "easy": dict(max_depth=2, time_limit=1.0, noise=250),
    "medium": dict(max_depth=4, time_limit=3.0, noise=0),
    "hard": dict(max_depth=7, time_limit=5.0, noise=0),
}


def choose_action(state: tuple, difficulty: str = "medium",
                  time_limit: float | None = None,
                  rng: random.Random | None = None,
                  history_counts: dict | None = None):
    cfg = DIFFICULTIES[difficulty]
    action, _ = search(
        state,
        max_depth=cfg["max_depth"],
        time_limit=cfg["time_limit"] if time_limit is None else time_limit,
        noise=cfg["noise"],
        rng=rng,
        history_counts=history_counts,
    )
    return action
