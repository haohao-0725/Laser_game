# 07 Phase 3 — 對戰 AI（minimax + alpha-beta）

> **現行雙平台版本（Phase 7A / v1.2.1）**：下方保留 v1 的設計骨架與驗收歷史；
> 真正執行中的 `khet/ai.py` 與手機 `www/js/ai.js` 均已升級為 AI v2；手機版以
> Web Worker 執行相同搜尋架構，避免 3–5 秒搜尋阻塞 UI。

## AI v2 現行架構

- 迭代加深 PVS/negamax + alpha-beta + aspiration window。
- 置換表儲存 EXACT/LOWER/UPPER，mate score 以 ply 正規化；重複兩次以上的歷史摘要納入 key。
- 搜尋路徑逐層維護完整 state 次數，同一 state 第三次出現直接回傳 `DRAW = 0`。
- 排序：立即殺王 → 有利雷射吃子 → TT best → killer → history heuristic → 一般行動。
- 不穩定局面啟動選擇性 quiescence；只結算會改變目前光路的行動，避免分支失控。
- 評估包含材料、法老肉盾/逃生、Scarab 換位、反射節點、連續法老光路壓力、
  自傷與盾牌吸收壓力。
- 搜尋層以小型 LRU 快取合法行動，以 feature cache 重用相同 pieces 的盤面摘要；
  子局面只在走法真的被搜尋時才惰性套用，讓 alpha-beta 剪枝省下規則結算；
  不複製規則引擎，`apply_action` 仍是唯一行動真值。
- Medium 名義深度 4／3 秒；先快速完成深度 3，再用剩餘時間嘗試第 4 層。
  棋子剩 16 顆以下時額外提高一層目標深度，10 顆以下提高兩層，以改善少子收尾。
- 評估只掃描法老與 Scarab 的局部鄰域，不再對每顆棋重算八方向機動性；光路壓力改用
  到敵方法老的連續距離，並在 quiescence 中納入能避開己方雷射自傷的應手。
- 根節點對「第二次回到舊局面」施加小幅降權；第三次同形仍嚴格回傳 0 分正式和局。
- `search()` 的 info 會回報 depth/score/nodes/qnodes/tt_hits/cutoffs/root_scores。

桌面和局歷史必須由 GUI 的 `position_counts` 傳入 `choose_action()`；selfplay 報告要把
`draw_repetition` 與 `draw_ply_cap` 分開，禁止再合併成一個無法追溯的 `draw`。

前置：Phase 1 全綠（Phase 2 可並行）。產出物：`khet/ai.py`、`scripts/selfplay.py`。
里程碑：中等難度穩定擊敗隨機走子 95%+，體感「有在防守法老」。

## 架構總覽

迭代加深的 negamax + alpha-beta + 置換表。分支因子約 60-120，
目標：深度 4-6 層在 3 秒內出手（Python 做得到，別急著換語言）。

## 參考骨架：`khet/ai.py`

```python
"""對戰 AI。引擎之上的純搜尋層，同樣禁止 GUI 依賴。"""
import random
import time

from khet.engine import legal_actions, apply_action, winner, board_map, other

PIECE_VALUE = {"PHARAOH": 100000, "ANUBIS": 900, "PYRAMID": 500, "SCARAB": 0, "SPHINX": 0}
WIN_SCORE = 1_000_000


def evaluate(state, me):
    """正值 = 對 me 有利。v1 三成分：子力、法老安全、雷射威脅。"""
    player, pieces = state
    w = winner(state)
    if w is not None:
        return WIN_SCORE if w == me else -WIN_SCORE

    score = 0
    pharaohs = {}
    for p in pieces:
        v = PIECE_VALUE[p[0]]
        score += v if p[1] == me else -v
        if p[0] == "PHARAOH":
            pharaohs[p[1]] = p

    # 法老安全度：法老周邊 8 格的己方棋數（肉盾）- 空曠度
    occ = board_map(pieces)
    for color, ph in pharaohs.items():
        guard = sum(1 for dc in (-1, 0, 1) for dr in (-1, 0, 1)
                    if (dc or dr) and occ.get((ph[2] + dc, ph[3] + dr), (None, color))[1] == color)
        score += (guard * 40) if color == me else -(guard * 40)

    # 雷射威脅：模擬雙方「現在就發射」會打掉什麼（便宜又有效的一手威脅偵測）
    from khet.engine import resolve_laser
    for color in ("RED", "SILVER"):
        _, res = resolve_laser(pieces, color)
        if res.event == "hit":
            victim_type, victim_color = res.hit_piece[0], res.hit_piece[1]
            v = PIECE_VALUE[victim_type] // 2 + 50
            if victim_type == "PHARAOH":
                v = 5000                       # 下一手可能致命
            score += v if victim_color != me else -v  # 打到誰就對誰不利
            # 注意：這是「若 color 現在射」的假想，粗略但夠 v1 用
    return score


class TranspositionTable(dict):
    pass   # state -> (depth, score, flag, best_action)；v1 直接用 dict 即可


def search(state, max_depth, time_limit=3.0, rng=None):
    """迭代加深，回傳 (best_action, info)。"""
    me = state[0]
    tt = TranspositionTable()
    deadline = time.monotonic() + time_limit
    best = None

    def negamax(st, depth, alpha, beta, color_sign):
        if time.monotonic() > deadline:
            raise TimeoutError
        w = winner(st)
        if w is not None or depth == 0:
            return color_sign * evaluate(st, me)
        key = st
        entry = tt.get(key)
        order = legal_actions(st)
        if entry and entry[3] in order:            # 上輪最佳手排最前
            order.remove(entry[3]); order.insert(0, entry[3])
        best_local, best_act = -WIN_SCORE * 2, None
        for a in order:
            nst, res = apply_action(st, a)
            val = -negamax(nst, depth - 1, -beta, -alpha, -color_sign)
            if val > best_local:
                best_local, best_act = val, a
            alpha = max(alpha, val)
            if alpha >= beta:
                break
        tt[key] = (depth, best_local, "exact", best_act)
        return best_local

    for depth in range(1, max_depth + 1):
        try:
            acts = legal_actions(state)
            if rng:
                rng.shuffle(acts)                   # 難度噪音入口
            scored = []
            for a in acts:
                nst, _ = apply_action(state, a)
                scored.append((-negamax(nst, depth - 1, -WIN_SCORE * 2, WIN_SCORE * 2, -1), a))
            scored.sort(key=lambda x: -x[0])
            best = scored[0][1]
        except TimeoutError:
            break
    return best


def choose_action(state, difficulty="medium"):
    cfg = {
        "easy":   dict(max_depth=2, time_limit=1.0, noise=200),
        "medium": dict(max_depth=4, time_limit=3.0, noise=0),
        "hard":   dict(max_depth=6, time_limit=3.0, noise=0),
    }[difficulty]
    rng = random.Random()
    act = search(state, cfg["max_depth"], cfg["time_limit"],
                 rng if cfg["noise"] else None)
    return act
```

**這是骨架不是成品**：走法排序（吃子手優先）、置換表 flag（exact/lower/upper）、
Zobrist 雜湊加速，都是照教科書逐步加上去的優化。順序：
先讓它「正確地慢」→ 加最佳手排序 → 加吃子優先 → 量測 → 需要時才做 Zobrist。

## 走法排序建議（效益排序）

1. 置換表最佳手
2. 「射後有殺」的手（apply 後 `resolve_laser` 顯示能打到對方棋）——可先只對淺層做
3. 旋轉 Sphinx 的手通常放最後（多數時候是浪費一手）

## 效能量測（每次優化前後都要跑）

```powershell
.\venv\Scripts\python.exe scripts\selfplay.py --games 20 --p1 medium --p2 random --report
```

`scripts/selfplay.py` 規格：兩個玩家（random / easy / medium / hard）對打 N 局，
輸出勝率、平均每手思考時間、平均局長；`--seed` 可重現。它同時是迴歸測試
（AI 改壞會直接反映在勝率）與評估函數調參工具。

## 難度分級驗收

（深度 2/3/6 為 Python 效能實測後定案：開局分支因子 ~100，深度 4≈2s、深度 5≈20s。
中檔用固定深度 3 求快與穩；高檔靠時限 + 超時部分採用逼近 4-5 層。）

| 難度 | 深度上限 / 時限 | 額外 | 驗收 |
|---|---|---|---|
| easy | 2 / 1s | 評估加噪音（隨機擾動 ±250） | 新手能贏它 |
| medium | 4 / 3s | 先完成深度 3；少子局面延伸 | 對 random 勝率 ≥ 95% |
| hard | 7 / 5s | killer move + 超時部分採用 | 對 medium 勝率 ≥ 70% |

**必做的兩個搜尋細節**（沒有它們 hard 與 medium 會同強度）：
1. **超時部分採用**：迭代加深某輪超時，該輪已搜完的手仍採用其中最佳
   （排最前的是上輪最佳手，故只會變好不會變差）。
2. **根節點洗牌 + 重複局面降權**：否則兩個決定性 AI 對打每局完全相同，
   還會走進三次同形和局迴圈（把對局的 position_counts 傳進 choose_action）。

## 驗收標準

- [ ] `pytest` 新增 AI 測試通過：一步殺局面（把對方法老放在射線上）AI 必選殺著；
      被將死威脅時 AI 會擋
- [ ] selfplay medium vs random 20 局 ≥ 95% 勝
- [ ] medium 平均每手 < 3 秒（在本機 venv 量測）
- [ ] GUI 加入「人機對戰」模式選單（難度三檔），AI 思考時 GUI 不凍結
      （QThread 或 QTimer 分段跑；最簡單：`QThreadPool` + signal 回傳）
