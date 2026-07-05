"""謎題生成器：隨機殘局 → 求解器認證「恰好 N 手必勝」→ 寫入 data/puzzle_catalog.json。

用法：
    .\\venv\\Scripts\\python.exe scripts\\gen_puzzles.py                 # 跑到額度滿
    .\\venv\\Scripts\\python.exe scripts\\gen_puzzles.py --verify        # 重新認證現有目錄
    .\\venv\\Scripts\\python.exe scripts\\gen_puzzles.py --quota 17 17 5 # 各難度題數

每找到一題就即時寫檔（可中斷續跑：已有題目會載入並去重）。"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from khet.engine import (
    action_to_dict, action_from_dict, apply_action, initial_state,
    legal_actions, pieces_from_list, pieces_to_list, winner,
)
from khet.puzzles import SolveTimeout, forced_win_in

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "puzzle_catalog.json")
# 各難度（=必勝手數 N）認證時限：AND-OR 搜尋成本隨 N 指數成長
CERT_TIMEOUT = {1: 5.0, 2: 40.0, 3: 240.0}


def engine_fingerprint() -> str:
    with open(os.path.join(ROOT, "data", "laser_table.json"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def random_endgame(rng: random.Random):
    """官方佈局隨機走 30-80 步，再隨機拆掉 0-6 顆非關鍵棋 → 擬真殘局。"""
    state = initial_state(rng.choice(["classic", "imhotep", "dynasty"]))
    for _ in range(rng.randrange(30, 81)):
        if winner(state) is not None:
            return None
        state, _ = apply_action(state, rng.choice(legal_actions(state)))
    player, pieces = state
    removable = [p for p in pieces if p[0] in ("PYRAMID", "ANUBIS", "SCARAB")]
    rng.shuffle(removable)
    for p in removable[:rng.randrange(0, 7)]:
        pieces = tuple(x for x in pieces if x != p)
    return (player, tuple(sorted(pieces)))


def certify(state, max_n: int):
    """回傳 (n, 致勝首著) —— 恰好 n 手必勝；無解回 None。逐 n 遞增天然保證「恰好」。"""
    me = state[0]
    for n in range(1, max_n + 1):
        try:
            sol = forced_win_in(state, me, n, timeout=CERT_TIMEOUT[n])
        except SolveTimeout:
            return None                      # 認證不完就放棄這個候選
        if sol is not None:
            return (n, sol)
    return None


def load_catalog() -> dict:
    if os.path.exists(CATALOG):
        with open(CATALOG, encoding="utf-8") as f:
            return json.load(f)
    return {"generated": str(date.today()),
            "engine_fingerprint": engine_fingerprint(), "puzzles": []}


def save_catalog(cat: dict) -> None:
    cat["generated"] = str(date.today())
    cat["engine_fingerprint"] = engine_fingerprint()
    cat["puzzles"].sort(key=lambda p: (p["difficulty"], p["id"]))
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1)


def verify_catalog() -> int:
    cat = load_catalog()
    if cat["engine_fingerprint"] != engine_fingerprint():
        print("FAIL: engine_fingerprint 不符（規則表變了，全部謎題需重新認證）")
        return 1
    for p in cat["puzzles"]:
        state = (p["player"], pieces_from_list(p["pieces"]))
        n = p["difficulty"]
        sol = forced_win_in(state, p["player"], n, timeout=CERT_TIMEOUT[n] * 2)
        assert sol is not None, f"{p['id']}: {n} 手必勝驗證失敗"
        if n > 1:
            assert forced_win_in(state, p["player"], n - 1,
                                 timeout=CERT_TIMEOUT[n - 1] * 2) is None, \
                f"{p['id']}: 其實 {n - 1} 手就能贏（難度標錯）"
        # 記錄的解答首著必須真的有效
        mid, _ = apply_action(state, action_from_dict(p["solution_first_move"]))
        assert winner(mid) == p["player"] if n == 1 else winner(mid) in (None, p["player"])
        print(f"OK: {p['id']}（{n} 手）")
    print(f"OK: 目錄 {len(cat['puzzles'])} 題全部通過")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--quota", type=int, nargs=3, default=[17, 17, 5],
                    metavar=("N1", "N2", "N3"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-candidates", type=int, default=100000)
    args = ap.parse_args()

    if args.verify:
        return verify_catalog()

    rng = random.Random(args.seed)
    cat = load_catalog()
    quota = {1: args.quota[0], 2: args.quota[1], 3: args.quota[2]}
    have = {1: 0, 2: 0, 3: 0}
    seen = set()
    for p in cat["puzzles"]:
        have[p["difficulty"]] += 1
        seen.add((p["player"], pieces_from_list(p["pieces"])))

    t0 = time.monotonic()
    tried = 0
    while any(have[n] < quota[n] for n in (1, 2, 3)) and tried < args.max_candidates:
        tried += 1
        state = random_endgame(rng)
        if state is None or state in seen:
            continue
        # 只認證還缺額度的難度範圍
        max_needed = max(n for n in (1, 2, 3) if have[n] < quota[n])
        result = certify(state, max_needed)
        if result is None:
            continue
        n, sol = result
        if have[n] >= quota[n]:
            continue
        have[n] += 1
        seen.add(state)
        pid = f"n{n}_{have[n]:03d}"
        cat["puzzles"].append({
            "id": pid,
            "difficulty": n,
            "player": state[0],
            "pieces": pieces_to_list(state[1]),
            "solution_first_move": action_to_dict(sol),
        })
        save_catalog(cat)
        el = time.monotonic() - t0
        print(f"[{el:7.0f}s] 收錄 {pid}（候選 {tried}）— 進度 "
              f"N1:{have[1]}/{quota[1]} N2:{have[2]}/{quota[2]} N3:{have[3]}/{quota[3]}",
              flush=True)

    print(f"完成：N1={have[1]} N2={have[2]} N3={have[3]}（嘗試 {tried} 個候選）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
