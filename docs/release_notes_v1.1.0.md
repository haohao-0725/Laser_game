# 雷射對決 Laser Duel v1.1.0（Windows 桌面版）

本次版本專注於桌面 AI 與和局正確性；Android 手機版維持 v1.0，未包含本次 AI 更新。

## AI v2

- 三次同形已成為完整搜尋終局，AI 能正確評估逼和、避和與接受和局。
- 搜尋升級為迭代加深 PVS、aspiration window、history heuristic 與 repetition-aware TT。
- 立即殺王、雷射吃子與強制戰術優先搜尋；不穩定光路使用選擇性 quiescence。
- 評估新增法老逃生與光路危險、機動性、Scarab 換位、反射控制、自傷與 blocker 壓力。
- 重用已展開的近根局面與盤面特徵，兼顧搜尋速度並維持規則引擎單一真值。

## 規則與工具修正

- 桌面版三次同形後會真正停止人類與背景 AI 繼續落子；悔棋與開新局仍可使用。
- self-play 分開統計正式三次同形與測試手數上限，並修正局長多算一手的問題。

## 驗證

- pytest：116 passed。
- Classic medium vs random：20/20 勝（每手限制 0.2 秒），0 正式和局、0 手數截斷。
- Classic AI v2 vs v1：3 勝 0 敗、1 局達測試上限（雙方交換先後手，固定種子）。
- Windows one-file exe 由專案 PyInstaller spec 重新建置並通過 smoke test。

## 下載與執行

下載 `LaserDuel_v1.1.0_win64.zip`，解壓後執行 `LaserDuel.exe`。支援 Windows 10/11 64 位元。
