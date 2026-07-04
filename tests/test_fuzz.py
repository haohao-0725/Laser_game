"""隨機自對戰煙霧測試：預設快速版（CI 每次跑）。
Phase 1 驗收的 10 萬步版本：
    $env:KHET_FUZZ_PLIES = "100000"; .\\venv\\Scripts\\python.exe -m pytest tests\\test_fuzz.py -q
"""
import os
import random

from khet.engine import initial_state, legal_actions, apply_action, winner

TARGET_PLIES = int(os.environ.get("KHET_FUZZ_PLIES", "8000"))   # 總隨機走子步數
MAX_PLIES_PER_GAME = 200


def test_random_selfplay_no_crash():
    rng = random.Random(20260704)
    plies_done = 0
    games = 0
    while plies_done < TARGET_PLIES:
        games += 1
        layout = rng.choice(["classic", "imhotep", "dynasty"])
        state = initial_state(layout)
        for _ in range(MAX_PLIES_PER_GAME):
            if winner(state) is not None:
                break
            acts = legal_actions(state)
            assert acts, "無合法行動（規則上不可能：至少能旋轉 Sphinx）"
            state, _res = apply_action(state, rng.choice(acts))
            plies_done += 1
            # 不變量檢查
            _, pieces = state
            assert len({(p[2], p[3]) for p in pieces}) == len(pieces), "棋子重疊"
            assert all(0 <= p[2] < 10 and 0 <= p[3] < 8 for p in pieces), "棋子出界"
            assert sum(1 for p in pieces if p[0] == "SPHINX") == 2, "SPHINX 消失"
            assert sum(1 for p in pieces if p[0] == "SCARAB") == 4, "SCARAB 被移除（不可能）"
            for p in pieces:
                opponent = "SILVER" if p[1] == "RED" else "RED"
                from khet.engine import RESTRICTED
                assert (p[2], p[3]) not in RESTRICTED[opponent], f"{p} 停在對方限制格"
    print(f"fuzz: {plies_done} plies / {games} games OK")
