# 雷射對決 Laser Duel v1.2.0（Windows 桌面版）

本次版本強化桌面 AI v2 的跨版圖棋力、戰術穩定性與搜尋效率；Android 手機版維持
v1.0，未包含本次 AI 更新。

## AI 棋力強化

- Medium 先穩定完成深度 3，再使用 3 秒預算嘗試深度 4。
- 少子局面自動增加搜尋目標深度，改善殘局逼殺與收尾。
- 光路評估改為連續法老壓力，降低只追求光路長度或無效機動性的偏差。
- quiescence 現在會搜尋能避免己方雷射自傷的強制應手。
- 第二次回到舊局面時小幅降權；第三次同形仍嚴格依規則評為和局。

## 搜尋效率與驗證工具

- 子局面改為惰性套用，alpha-beta 剪枝後不再結算用不到的合法行動。
- 靜態評估只掃描法老、Scarab 局部鄰域與實際光路，降低葉節點成本。
- 新增跨版本／跨版圖競技工具，可重現 v2 vs v1 與 v2 vs v2 結果。

## 驗證

- pytest：117 passed。
- 跨 Classic、Imhotep、Dynasty 的 AI v2 vs v1：10 勝 0 敗（每手 3 秒）。
- 同限制深度 3 的隔離測試：v2 2 勝 0 敗、1 局達手數上限。
- AI v2 自我對弈：Silver 6 勝、Red 2 勝、2 局達手數上限；0 次三次同形和局
  （每手 1 秒）。
- Windows one-file exe 由專案 PyInstaller spec 重新建置並通過 smoke test。

## 下載與執行

下載 `LaserDuel_v1.2.0_win64.zip`，解壓後執行 `LaserDuel.exe`。支援 Windows 10/11 64 位元。
