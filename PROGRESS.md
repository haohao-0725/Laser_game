# 專案進度儀表板（每個 session 結束前更新這裡）

> 使用方式見 `docs/agent_manual/00_INDEX.md`。原則：這個檔案永遠反映**現在的真實狀態**，
> 讓下一個接手的 agent 30 秒內知道要做什麼。

## 目前狀態

- **階段**：Phase 0 完成 ✅ → **下一步：Phase 1 規則引擎**
- **下一個具體動作**：讀 `docs/agent_manual/04_phase1_engine.md`，
  建立 `khet/engine.py`（章內有完整參考實作），接著照 05 章建測試，全綠後回來更新本檔。

## Phase 總表

| Phase | 內容 | 狀態 | 完成日 |
|---|---|---|---|
| 0 | 規格定案 + 規則查證 + 環境 + 手冊 | ✅ 完成 | 2026-07-04 |
| 1 | 規則引擎 + 測試 | ⬜ 未開始 | |
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
| 2026-07-04 | Phase 0：環境 + 規則查證 + 資料檔 + 手冊全套 | validate_layouts ✅ / gen_laser_table 自檢 ✅ / pytest（尚無測試） |
