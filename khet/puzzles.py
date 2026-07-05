"""謎題求解器：「N 手內必勝（對方任意應手）」的 AND-OR 搜尋。
純引擎層之上，無 GUI 依賴。手數計算：n=1 表示我走 1 步就贏；
n=2 表示我走、對方任意應、我再走必贏。"""
from __future__ import annotations

import time

from khet.engine import apply_action, legal_actions, winner


class SolveTimeout(Exception):
    pass


class Solver:
    """帶記憶化與時限的 AND-OR 求解器。同一 Solver 可重複查詢（memo 共用）。"""

    def __init__(self, me: str, deadline: float | None = None):
        self.me = me
        self.deadline = deadline
        self.memo: dict = {}
        self.nodes = 0

    def _tick(self) -> None:
        self.nodes += 1
        if (self.deadline is not None and self.nodes % 512 == 0
                and time.monotonic() > self.deadline):
            raise SolveTimeout

    def win_or(self, state: tuple, moves_left: int):
        """輪到 me（OR 節點）：回傳致勝首著，無則 None。"""
        key = (state, moves_left)
        if key in self.memo:
            return self.memo[key]
        self._tick()
        result = None
        survivors = []
        for a in legal_actions(state):
            child, _ = apply_action(state, a)
            w = winner(child)
            if w == self.me:
                result = a
                break
            if w is not None:                  # 自殺手，跳過
                continue
            survivors.append((a, child))
        if result is None and moves_left > 1:
            for a, child in survivors:
                if self.win_and(child, moves_left - 1):
                    result = a
                    break
        self.memo[key] = result
        return result

    def win_and(self, state: tuple, moves_left: int) -> bool:
        """輪到對方（AND 節點）：對方所有應手都擋不住才回傳 True。"""
        key = (state, moves_left)
        if key in self.memo:
            return self.memo[key]
        self._tick()
        ok = True
        for a in legal_actions(state):
            child, _ = apply_action(state, a)
            w = winner(child)
            if w == self.me:                   # 對方自殺，此分支我贏
                continue
            if w is not None:                  # 對方反殺
                ok = False
                break
            if self.win_or(child, moves_left) is None:
                ok = False
                break
        self.memo[key] = ok
        return ok


def forced_win_in(state: tuple, me: str, n: int,
                  timeout: float | None = None):
    """me 是否能在 n 手內必勝？回傳致勝首著或 None。超時丟 SolveTimeout。"""
    deadline = None if timeout is None else time.monotonic() + timeout
    return Solver(me, deadline).win_or(state, n)


def best_defense(state: tuple, attacker: str, moves_left: int,
                 timeout: float | None = None):
    """防守方（state 目前輪到的一方）的最佳應手：
    優先找能破解「attacker 在 moves_left 手內必勝」的手；
    找不到就回傳任何不立即輸的手（垂死掙扎）；再不行回傳任意合法手。"""
    deadline = None if timeout is None else time.monotonic() + timeout
    solver = Solver(attacker, deadline)
    fallback = None
    any_action = None
    for a in legal_actions(state):
        child, _ = apply_action(state, a)
        if any_action is None:
            any_action = a
        w = winner(child)
        if w == attacker:
            continue
        if w is not None:                      # 反殺！
            return a
        if fallback is None:
            fallback = a
        try:
            if solver.win_or(child, moves_left) is None:
                return a                       # 成功破解
        except SolveTimeout:
            return a                           # 算不完就當作能撐
    return fallback if fallback is not None else any_action
