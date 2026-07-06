"""生成規則一致性向量：Python 走隨機子產生 (state_in, action, state_out, path, event)，
輸出 www/test_vectors.json，供 JS 端逐一比對，證明雙平台規則零差異。
執行：.\\venv\\Scripts\\python.exe scripts\\gen_test_vectors.py [--count 500]
"""
import argparse
import json
import os
import random

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from khet.engine import (
    action_to_dict, apply_action, initial_state, legal_actions,
    pieces_to_list, winner,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def state_to_dict(state):
    return {"player": state[0], "pieces": pieces_to_list(state[1])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260706)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    vectors = []
    while len(vectors) < args.count:
        state = initial_state(rng.choice(["classic", "imhotep", "dynasty"]))
        for _ in range(200):
            if winner(state) is not None:
                break
            action = rng.choice(legal_actions(state))
            new_state, res = apply_action(state, action)
            vectors.append({
                "state_in": state_to_dict(state),
                "action": action_to_dict(action),
                "state_out": state_to_dict(new_state),
                "path": [list(c) for c in res.path],
                "event": res.event,
                "hit": list(res.hit_piece) if res.hit_piece else None,
            })
            state = new_state
            if len(vectors) >= args.count:
                break

    out = os.path.join(ROOT, "www", "test_vectors.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: 生成 {len(vectors)} 條向量 → {out}")


if __name__ == "__main__":
    main()
