# 專案進度儀表板（每個 session 結束前更新這裡）

> 使用方式見 `docs/agent_manual/00_INDEX.md`。原則：這個檔案永遠反映**現在的真實狀態**，
> 讓下一個接手的 agent 30 秒內知道要做什麼。

## 目前狀態

- **階段**：Phase 1 完成 ✅ → **下一步：Phase 2 桌面 GUI**
- **下一個具體動作**：讀 `docs/agent_manual/06_phase2_gui.md`，建立 `gui/` 套件與 `main.py`。
  ⚠️ 注意：`assets/` 的圖片使用者還在製作中（目前資料夾裡是未改名的原始檔，已被 gitignore），
  GUI 一律先用 QPainter 佔位圖形，寫成「檔案存在才用圖」的 fallback 模式。

## Phase 總表

| Phase | 內容 | 狀態 | 完成日 |
|---|---|---|---|
| 0 | 規格定案 + 規則查證 + 環境 + 手冊 | ✅ 完成 | 2026-07-04 |
| 1 | 規則引擎 + 測試 | ✅ 完成 | 2026-07-04 |
| 2 | 桌面 GUI（PyQt6） | ⬜ 未開始 | |
| 3 | 對戰 AI | ⬜ 未開始 | |
| 4 | 謎題模式 | ⬜ 未開始 | |
| 5 | 打磨 + 桌面發布 v1.0 | ⬜ 未開始 | |
| 6 | 手機版 APK | ⬜ 未開始 | |

（Phase 4 與 5 順序可對調，見 roadmap。正式名稱未定，發布前要問使用者。）

## 已完成的地基（Phase 0，2026-07-04）

- venv 建立（Python 3.10.8 + PyQt6 6.7.1 + pytest 8.3.3 + pyinstaller，鎖版 requirements.txt）
- 規則三項【待查證】全部查證完畢（限制格/Sphinx/三種佈局），來源與方法見手冊 03 章 §7
- `data/layouts.json`（權威佈局資料）＋ `scripts/validate_layouts.py`（驗證通過）
- `data/laser_table.json`（由 `scripts/gen_laser_table.py` 生成，內建自檢通過）
- Agent 手冊 `docs/agent_manual/00-10` 全套

## 異常記錄（發現文件矛盾、規則疑義、環境問題都記在這）

（目前無）

## Session 日誌（最新在上，一行一 session）

| 日期 | 做了什麼 | 測試狀態 |
|---|---|---|
| 2026-07-04 | Phase 1：khet/engine.py + 三個測試檔；AGENT.md 改寫；assets 原始圖改為 gitignore | pytest 94 passed ✅ / 10 萬步 fuzz（100036 plies / 2039 games）✅ / 引擎 0 Qt import ✅ |
| 2026-07-04 | Phase 0：環境 + 規則查證 + 資料檔 + 手冊全套 | validate_layouts ✅ / gen_laser_table 自檢 ✅ / pytest（尚無測試） |
