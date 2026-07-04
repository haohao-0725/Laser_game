# 03 規則完整參考（已查證版，取代 rules_spec.md 的【待查證】）

本章是遊戲規則的最終依據。座標/朝向記法見 [01_conventions.md](01_conventions.md)。

## 1. 棋盤與限制格

- 10 欄 × 8 列。紅方在上（row 0 側）、銀方在下（row 7 側）。
- 限制格（已查證，權威資料在 `data/layouts.json`）：
  - **紅方專用**：a 欄整欄（a1–a8）＋ i8 ＋ i1
  - **銀方專用**：j 欄整欄（j1–j8）＋ b8 ＋ b1
- 限制規則：對方棋子不可**移入**、不可**經換位被換入**這些格。雷射光束不受限制格影響。
- a8 = 紅 Sphinx 固定座、j1 = 銀 Sphinx 固定座。

## 2. 棋子（每方 13 顆）

1 PHARAOH、1 SPHINX、2 SCARAB、2 ANUBIS、7 PYRAMID。互動細節見 01 章表格與
`data/laser_table.json`。要點：

- SPHINX：不可移動、免疫雷射。**只能旋轉**，且只有 2 個合法朝向：
  紅（a8）朝 E 或 S；銀（j1）朝 N 或 W（即只能沿己方那條欄/列發射，不可朝棋盤外）。
- SCARAB 換位（swap）：可與**相鄰 8 格**的 PYRAMID 或 ANUBIS 交換位置，**不分敵我**；
  不可與 PHARAOH、SCARAB、SPHINX 換。換位時兩顆棋的朝向都不變。
  換位不可把任一顆棋子放進它不可停留的限制格。
- SCARAB 是雙面鏡，永遠反射 → 永遠不可能被移除。

## 3. 回合流程

1. 行動（必選其一，不可跳過）：
   a. 移動自己一顆棋到相鄰空格（8 方向）；SCARAB 可改為換位；SPHINX 不可移動。
   b. 原地旋轉自己一顆棋 90°（順或逆）；SPHINX 只能在其 2 個合法朝向間切換。
2. 行動後**自己的 Sphinx 強制自動發射**雷射（不可放棄、不可試射）。
3. 依 §4 解算光束；被打中弱點的棋子移除（**己方棋子同樣會被自己打掉**）。
4. 任一方 PHARAOH 被移除 → 對方立即獲勝（自己射掉自己的法老 = 自己輸）。
5. 換對方回合。**銀方先手**。

## 4. 雷射解算

```
pos = 己方 Sphinx 座標；dir = Sphinx 朝向
loop（上限 500 步保險）:
    pos = pos 往 dir 前進一格
    若出界 → 光束結束，無事
    若該格無棋子 → 繼續
    若有棋子 → 查 laser_table[type][orientation][dir]:
        reflect(newdir) → dir = newdir，繼續
        absorb          → 光束結束
        hit             → 移除該棋子，光束結束
```

- 每回合最多移除 1 顆棋子。
- 光束完整路徑（含轉折點與終點事件）要回傳給呼叫端，GUI 動畫靠它。

## 5. 勝負與和局

- 勝：對方 PHARAOH 被移除（含對方自傷）。
- 和：**三次同形**（同一局面第三次出現，含輪到誰走）。第一版引擎就要偵測
  （用 state tuple 當 key 數次數即可），GUI 顯示「和局」。
- 雙方同意和局：GUI 加個按鈕即可，引擎不用管。

## 6. 官方初始佈局

三種：`classic`（標準）、`imhotep`（Classic 變體，換位防禦向）、`dynasty`（攻守平衡、節奏快）。
完整座標與朝向在 `data/layouts.json`（已查證，勿改）。

## 7. 查證記錄（為什麼可以信任這份資料）

2026-07-04 由主力 agent 完成查證，方法與來源：

1. **限制格與規則文字**：Laser Chess（ThinkFun，Khet 2.0 官方再版，同一位發明人
   Luke Hooper）規則文件，取自 kishannareshpal/laserchess 的 docs/Guide.md
   （逐格列出 reserved cells）；與 alaingilbert/khet（Khet 2.0 實作）
   main.js 中 ankh/eye 符號繪製座標**完全一致**（兩個獨立來源）。
2. **三種佈局**：alaingilbert/khet 的 levels/*.js；其中 classic 與 laserchess 的
   Ace 佈局逐棋比對，13 顆棋位置與朝向**全部一致**；imhotep/dynasty 通過
   180° 旋轉對稱檢查（scripts/validate_layouts.py 可隨時重跑）。
3. **朝向語意**：解析 laserchess 的 SVG 向量檔確定 0° 基準（Deflector 鏡面、
   Defender 盾面、Laser 砲口），再以「開局光束路徑」做物理驗證：
   classic 開局雙方光束路徑完美鏡像且無害出界
   （銀：j1→j4→h4→h5→j5→出界；紅：a8→a5→c5→c4→a4→出界）。
4. **三次同形和局**：Khet 官方規則書文字（ultraboardgames/officialgamerules 轉載）
   與 Wikipedia 皆確認「As in chess, three-fold repetition of the position is a draw」。
5. **先手**：Khet 銀方先手 = Laser Chess 藍方先手（官方對應色）。

若未來需要重新查證，來源：en.wikipedia.org/wiki/Khet_(game)、
github.com/kishannareshpal/laserchess、github.com/alaingilbert/khet。
