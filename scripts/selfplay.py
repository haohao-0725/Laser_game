"""AI 自動對戰：迴歸測試 + 評估函數調參 + 強度驗收。

用法（專案根目錄）：
    .\\venv\\Scripts\\python.exe scripts\\selfplay.py --games 20 --p1 medium --p2 random
    .\\venv\\Scripts\\python.exe scripts\\selfplay.py --games 10 --p1 hard --p2 medium --time-limit 1.0

p1/p2 可為 random / easy / medium / hard。每局輪流先手（銀方），確保公平。
"""
import argparse
import random
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 2)[0])  # 專案根目錄

from khet.ai import choose_action
from khet.engine import initial_state, legal_actions, apply_action, winner

MAX_PLIES = 200


def make_player(name: str, time_limit: float | None):
    if name == "random":
        return (lambda state, rng, counts: rng.choice(legal_actions(state))), False
    return (lambda state, rng, counts: choose_action(
        state, name, time_limit=time_limit, rng=rng, history_counts=counts)), True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--p1", default="medium")
    ap.add_argument("--p2", default="random")
    ap.add_argument("--seed", type=int, default=20260705)
    ap.add_argument("--time-limit", type=float, default=None,
                    help="覆蓋 AI 每手秒數上限（驗收快速跑可用 1.0）")
    ap.add_argument("--layout", default="classic")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    fn1, ai1 = make_player(args.p1, args.time_limit)
    fn2, ai2 = make_player(args.p2, args.time_limit)
    wins = {args.p1 + "(p1)": 0, args.p2 + "(p2)": 0, "draw": 0}
    think_time = {1: [], 2: []}
    lengths = []

    for g in range(args.games):
        # 輪流先手：偶數局 p1 執銀、奇數局 p2 執銀
        silver_is_p1 = (g % 2 == 0)
        state = initial_state(args.layout)
        counts = {state: 1}
        result = "draw"
        for ply in range(MAX_PLIES):
            w = winner(state)
            if w is not None:
                p1_color = "SILVER" if silver_is_p1 else "RED"
                result = args.p1 + "(p1)" if w == p1_color else args.p2 + "(p2)"
                break
            if counts.get(state, 0) >= 3:
                break                       # 三次同形判和
            is_p1_turn = (state[0] == "SILVER") == silver_is_p1
            fn, is_ai, idx = (fn1, ai1, 1) if is_p1_turn else (fn2, ai2, 2)
            t0 = time.monotonic()
            action = fn(state, rng, counts)
            if is_ai:
                think_time[idx].append(time.monotonic() - t0)
            state, _ = apply_action(state, action)
            counts[state] = counts.get(state, 0) + 1
        else:
            ply = MAX_PLIES
        wins[result] += 1
        lengths.append(ply + 1)
        print(f"game {g + 1}/{args.games}: {result}（{ply + 1} 手）", flush=True)

    print("\n===== 報告 =====")
    total = args.games
    for k, v in wins.items():
        print(f"{k}: {v}/{total} ({100.0 * v / total:.0f}%)")
    print(f"平均局長: {sum(lengths) / len(lengths):.1f} 手")
    for idx, name, is_ai in ((1, args.p1, ai1), (2, args.p2, ai2)):
        if is_ai and think_time[idx]:
            ts = think_time[idx]
            print(f"{name}(p{idx}) 平均思考 {sum(ts) / len(ts):.2f}s / 最大 {max(ts):.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
