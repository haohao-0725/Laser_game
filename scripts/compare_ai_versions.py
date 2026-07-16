"""跨版圖比較目前桌面 AI、舊版 AI 與自我對弈。

舊版由 Git revision 直接載入，避免在正式套件複製一份過時搜尋器。
"""
from __future__ import annotations

import argparse
from collections import Counter
import random
import subprocess
import sys
import time
from types import ModuleType

sys.path.insert(0, __file__.rsplit("\\", 2)[0])

from khet.ai import search as search_v2
from khet.engine import apply_action, initial_state, legal_actions, winner


def load_legacy_search(revision: str):
    source = subprocess.run(
        ["git", "show", f"{revision}:khet/ai.py"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    module = ModuleType("khet_ai_legacy")
    exec(compile(source, f"{revision}:khet/ai.py", "exec"), module.__dict__)
    return module.search


def play_game(layout: str, silver_engine: str, red_engine: str, searches: dict,
              depths: dict, time_limit: float, max_plies: int,
              rng: random.Random, verbose: bool = False) -> dict:
    state = initial_state(layout)
    counts = {state: 1}
    times = {"v1": [], "v2": []}
    depths_seen = {"v1": [], "v2": []}
    captures = 0
    self_hits = {"SILVER": 0, "RED": 0}
    quiet_tail = 0

    for ply in range(1, max_plies + 1):
        engine = silver_engine if state[0] == "SILVER" else red_engine
        kwargs = {
            "max_depth": depths[engine],
            "time_limit": time_limit,
            "rng": rng,
            "history_counts": counts,
        }
        started = time.monotonic()
        action, info = searches[engine](state, **kwargs)
        times[engine].append(time.monotonic() - started)
        depths_seen[engine].append(info.get("depth", 0))
        mover = state[0]
        state, laser = apply_action(state, action)
        if verbose:
            hit = ""
            if laser.event == "hit":
                hit = f" hit={laser.hit_piece[1]}-{laser.hit_piece[0]}"
            print(
                f"  ply={ply:03d} {mover:6s} {engine} depth={info.get('depth', 0)} "
                f"score={info.get('score', '-')} action={action}{hit}",
                flush=True,
            )
        if laser.event == "hit":
            captures += 1
            self_hits[mover] += int(laser.hit_piece[1] == mover)
            quiet_tail = 0
        else:
            quiet_tail += 1
        counts[state] = counts.get(state, 0) + 1

        victor = winner(state)
        if victor is not None:
            if silver_engine == red_engine:
                outcome = victor.lower()
            else:
                outcome = silver_engine if victor == "SILVER" else red_engine
            break
        if counts[state] >= 3:
            outcome = "draw_repetition"
            break
    else:
        outcome = "draw_ply_cap"

    def average(values):
        return sum(values) / len(values) if values else 0.0

    return {
        "layout": layout,
        "outcome": outcome,
        "plies": ply,
        "captures": captures,
        "self_hits": self_hits,
        "quiet_tail": quiet_tail,
        "unique_ratio": len(counts) / sum(counts.values()),
        "max_repetition": max(counts.values()),
        "avg_time": {name: average(values) for name, values in times.items()},
        "avg_depth": {name: average(values) for name, values in depths_seen.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("v2-v1", "v2-v2"), default="v2-v1")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--time-limit", type=float, default=3.0)
    parser.add_argument("--max-plies", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--legacy-ref", default="6c5e7b5")
    parser.add_argument("--v1-depth", type=int, default=3)
    parser.add_argument("--v2-depth", type=int, default=4)
    parser.add_argument(
        "--layouts", default="classic,imhotep,dynasty",
        help="以逗號分隔並循環使用的版圖",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    legacy_search = load_legacy_search(args.legacy_ref)
    searches = {"v1": legacy_search, "v2": search_v2}
    depths = {"v1": args.v1_depth, "v2": args.v2_depth}
    layouts = tuple(item.strip() for item in args.layouts.split(",") if item.strip())
    valid_layouts = {"classic", "imhotep", "dynasty"}
    if not layouts or not set(layouts) <= valid_layouts:
        parser.error("--layouts 只能包含 classic、imhotep、dynasty")
    results = []
    rng = random.Random(args.seed)

    for index in range(args.games):
        layout = layouts[index % len(layouts)]
        if args.mode == "v2-v1":
            silver, red = (("v2", "v1") if index % 2 == 0 else ("v1", "v2"))
        else:
            silver = red = "v2"
        result = play_game(
            layout, silver, red, searches, depths,
            args.time_limit, args.max_plies, rng, args.verbose,
        )
        results.append(result)
        print(
            f"{index + 1:02d} {layout:7s} S={silver} R={red} "
            f"{result['outcome']} {result['plies']} ply "
            f"captures={result['captures']} self={result['self_hits']} "
            f"tail={result['quiet_tail']} repeat={result['max_repetition']}",
            flush=True,
        )

    outcomes = Counter(item["outcome"] for item in results)
    print("\nresults:", dict(outcomes))
    print("by layout:")
    for layout in layouts:
        subset = [item for item in results if item["layout"] == layout]
        print(f"  {layout}: {dict(Counter(item['outcome'] for item in subset))}")
    print(f"avg plies: {sum(item['plies'] for item in results) / len(results):.1f}")
    for engine in ("v1", "v2"):
        engine_times = [
            item["avg_time"][engine] for item in results
            if item["avg_time"][engine] > 0
        ]
        engine_depths = [
            item["avg_depth"][engine] for item in results
            if item["avg_depth"][engine] > 0
        ]
        if engine_times:
            print(
                f"{engine}: avg time {sum(engine_times) / len(engine_times):.3f}s, "
                f"avg depth {sum(engine_depths) / len(engine_depths):.2f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
