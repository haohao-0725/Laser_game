# 08 Phase 4 — 單人謎題模式（市面數位版都沒有的亮點）

前置：Phase 1 + Phase 3（會用到搜尋基礎）。
產出物：`khet/puzzles.py`、`scripts/gen_puzzles.py`、`data/puzzle_catalog.json`、GUI 謎題頁。
里程碑：17 題 × 3 難度的**離線認證**謎題目錄 + 「每日一題」介面。

## 概念（沿用前作 Ricochet Robots 的 endpoint design 思路）

謎題 =「給定局面，我方 N 手內必勝（對方任意應手都擋不住）」。
生成流程全部離線做：隨機殘局 → 求解器認證 → 寫進目錄 JSON → 遊戲執行時零等待載入。

## 1. 求解器：`khet/puzzles.py`

「N 手必勝」是 AND-OR 搜尋：我方手是 OR（存在一手可行），對方手是 AND（所有應手都輸）。

```python
"""謎題求解器：判定 player 是否能在 n 手內必勝（對方任意應手）。"""
from functools import lru_cache

from khet.engine import legal_actions, apply_action, winner


def forced_win_in(state, me, n, _memo=None):
    """me 在 n 手內（me 的手數）必勝？回傳致勝首著或 None。
    深度：n=1 → 我走1步就贏；n=2 → 我走、對方任意走、我再走必贏。"""
    if _memo is None:
        _memo = {}

    def win_or(st, moves_left):          # 輪到 me（OR 節點）
        key = (st, moves_left, "or")
        if key in _memo:
            return _memo[key]
        result = None
        for a in legal_actions(st):
            nst, _ = apply_action(st, a)
            w = winner(nst)
            if w == me:
                result = a; break
            if w is not None:            # 自殺手
                continue
            if moves_left > 1 and win_and(nst, moves_left - 1):
                result = a; break
        _memo[key] = result
        return result

    def win_and(st, moves_left):         # 輪到對方（AND 節點）
        key = (st, moves_left, "and")
        if key in _memo:
            return _memo[key]
        for a in legal_actions(st):
            nst, _ = apply_action(st, a)
            w = winner(nst)
            if w == me:                  # 對方自殺，這分支我贏
                continue
            if w is not None:            # 對方直接贏了
                _memo[key] = False
                return False
            if win_or(nst, moves_left) is None:
                _memo[key] = False
                return False
        _memo[key] = True
        return True

    return win_or(state, n)
```

效能備註：n=1 很快；n=2 約 100×100×100 = 10^6 局面等級，加 memo 可行；
n=3 會慢——生成期離線跑，慢沒關係（一題跑幾分鐘可接受），但要印進度。

## 2. 生成器：`scripts/gen_puzzles.py`

```
loop 直到收集夠：
  1. 隨機殘局：從官方佈局隨機走 30-80 步 → 再隨機移除 0-6 顆非關鍵棋
     （保留雙方 PHARAOH/SPHINX；這比純隨機擺棋更像真實局面）
  2. 若 winner 已定或雙方雷射現在就能殺王 → 丟棄（開場即死的爛題）
  3. 認證：forced_win_in(state, me, N) 有解 且 forced_win_in(state, me, N-1) 無解
     → 「恰好 N 手必勝」，收錄
  4. 記錄：state、先手方、N、致勝首著（給提示功能用）
難度：N=1 入門、N=2 中等、N=3 困難，各 17 題（湊不滿 3 手題可先出 1-2 手題發布）
```

## 3. 目錄格式：`data/puzzle_catalog.json`

```json
{
  "generated": "2026-07-XX",
  "engine_fingerprint": "<laser_table.json 的 sha256 前 12 碼>",
  "puzzles": [
    {
      "id": "n1_001",
      "difficulty": 1,
      "player": "SILVER",
      "pieces": [["PYRAMID","RED",3,4,2], ...],
      "solution_first_move": {"kind":"rotate","col":9,"row":7,"cw":true}
    }
  ]
}
```

`engine_fingerprint`：載入時比對目前 laser_table 雜湊，不合就拒載
（防止規則表變了、舊謎題失效卻沒人發現）。

## 4. GUI 謎題頁

- 謎題目錄頁：3 難度分頁 × 17 題格狀清單，通關打勾（記錄存 `%APPDATA%` 或專案旁 JSON）。
- 「每日一題」：`date.toordinal() % len(catalog)` 選題，全球同步不需要伺服器。
- 遊玩規則：玩家執謎題方；走出非最優手後若已不可能 N 手勝 → 提示「已超出步數，重試？」
  （判定方式：每步後重跑 forced_win_in(剩餘步數)——N≤3 時執行期可承受，
  太慢就只在玩家步數用盡時判定失敗）。
- 提示按鈕：顯示 `solution_first_move`（每題限用一次）。

## 驗收標準

- [ ] 求解器單元測試：手工構造的 1 手殺局面回傳正確殺著；1 手殺不掉的局面 n=1 回傳 None
- [ ] 目錄 ≥ 17 題 × 難度 1-2（難度 3 至少 5 題），全部離線認證通過
- [ ] `scripts/gen_puzzles.py --verify` 可重新認證整個目錄（迴歸測試）
- [ ] GUI 可玩每日一題與目錄任選題，通關記錄會保存
