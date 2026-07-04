# 雷射棋規則規格書（實作級）

依據 Khet 2.0 規則整理成可直接實作的規格。
**2026-07-04 更新：原【待查證】項目已全部查證完畢**（限制格、Sphinx 朝向、三種佈局），
查證方法與來源見 `docs/agent_manual/03_rules_reference.md` §7；
權威資料檔為 `data/layouts.json` 與 `data/laser_table.json`。
座標/朝向的最終定義以 `docs/agent_manual/01_conventions.md` 為準。

## 1. 棋盤

- **10 欄 × 8 列**（比西洋棋寬）。座標建議 `(row 0-7, col 0-9)`，Silver 在下、Red 在上。
- **限制格**（✅ 已查證）：僅限該色棋子進入/停留：
  - 紅方專用（10 格）：a 欄整欄（a1–a8）＋ i8 ＋ i1
  - 銀方專用（10 格）：j 欄整欄（j1–j8）＋ b8 ＋ b1
  - a8 / j1 同時是紅/銀 Sphinx 固定座。
  引擎需求：另一色不可移入（換位也不可把對方棋子換進去）；資料在 `data/layouts.json`。

## 2. 棋子（每方 13 顆）

| 數量 | 官方名 | 開發代號 | 雷射互動 | 移動 |
|---|---|---|---|---|
| 1 | Pharaoh 法老 | KING | 任一面被擊中 → 移除，該方**立即敗北** | 8 方向走 1 格 |
| 1 | Sphinx 獅身人面 | EMITTER | **免疫雷射**（任何面） | **不可移動**；只能旋轉，僅 2 個合法朝向（✅ 已查證）：紅方固定 a8、朝 E 或 S；銀方固定 j1、朝 N 或 W |
| 2 | Scarab 聖甲蟲 | TWIN_MIRROR | 兩面都是鏡子 → 永遠反射，**不可能被移除** | 8 方向走 1 格；**換位**：可移入相鄰的 Pyramid 或 Anubis 所在格（**不論敵我**），兩者交換位置（被換的棋子朝向不變） |
| 2 | Anubis 阿努比斯 | SHIELD | **正面**被擊中 → 無事發生（吸收）；側面/背面 → 移除 | 8 方向走 1 格 |
| 7 | Pyramid 金字塔 | MIRROR | 斜面（鏡面）被擊中 → 90° 反射；其餘兩個非鏡面 → 移除 | 8 方向走 1 格 |

**朝向表示法**：每顆棋子有 `orientation ∈ {0,1,2,3}`（90° 步進）。
- Pyramid 的鏡面是一條斜邊：orientation 決定鏡面連接哪兩個方向
  （例：orientation 0 = 鏡面反射「來自北的光→東」與「來自東的光→北」，其餘面為弱點）。
- Scarab 的鏡面是整條對角線，雙面反射：orientation 只有 2 種等價狀態（`/` 與 `\`）。
- Anubis 的正面朝 orientation 方向。

## 3. 回合流程

1. 行動（**必選其一，不可跳過**）：
   a. 把自己的一顆棋子移動 1 格（8 方向）到**空格**（Scarab 例外可換位；Sphinx 不可移動），或
   b. 把自己的一顆棋子原地旋轉 **90°**（順或逆時針擇一）。Sphinx 只能在其 2 個合法朝向間切換。
2. 行動結束後，**自己的 Sphinx 自動發射雷射**（強制，不可放棄）。
3. 解算光束（見 §4），若有棋子被擊中弱點 → 從棋盤移除（**己方棋子同樣會被自己打掉**——這是核心策略元素）。
4. 若任一方法老被移除 → 對方獲勝，遊戲立即結束。
5. 換對方回合。

## 4. 雷射解算（引擎核心）

```
beam = (從 Sphinx 所在格、沿其朝向射出)
loop:
  前進一格
  若出界 → 光束消失，結束
  若該格無棋子 → 繼續
  若有棋子：
    依「棋子類型 × 棋子朝向 × 光束方向」查表：
      REFLECT(新方向) → 改方向，繼續前進
      ABSORB          → 光束消失，結束（Anubis 正面、Sphinx 任何面）
      HIT             → 該棋子移除，光束消失，結束
```

- 查表建議做成 `LASER_TABLE[piece_type][orientation][beam_direction] → Reflect(dir) | Absorb | Hit`，
  純資料表可直接被 Python / JS 兩版共用（序列化成 JSON），從根源保證雙平台一致。
- 光束不可能無限循環：鏡子數量有限且每格單向通過即離開；仍建議加 `MAX_STEPS = 500` 保險。
- 一回合最多移除 1 顆棋子（光束遇到第一個非反射面即結束）。

## 5. 額外規則

- **三次同形判和**（✅ 已查證）：官方規則「同一局面第三次出現判和」（同西洋棋）。
  引擎用 state tuple 當 key 計數即可，由對局管理層實作。
- **初始佈局**（✅ 已查證）：Classic / Imhotep / Dynasty 三種，
  完整座標與朝向已存成 `data/layouts.json`（`scripts/validate_layouts.py` 驗證通過）。

## 6. 勝負與平局

- 勝：對方法老被移除（含對方自己誤射）。
- 平局：雙方同意，或（若實作）三次同形。

## 7. 引擎介面草案

```python
class KhetEngine:
    def legal_actions(state, player) -> list[Action]   # Move(cell, dir) | Rotate(cell, cw) | Swap(cell, dir)
    def apply(state, action) -> (new_state, LaserResult)  # 含光束路徑（給動畫）與被移除棋子
    def winner(state) -> None | 'Silver' | 'Red'
```

State 建議為不可變 tuple（棋子 = (type, color, orientation, cell)），
方便 minimax 的雜湊與 undo-free 搜尋。
