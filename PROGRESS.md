# 專案進度儀表板（每個 session 結束前更新這裡）

> 使用方式見 `docs/agent_manual/00_INDEX.md`。原則：這個檔案永遠反映**現在的真實狀態**，
> 讓下一個接手的 agent 30 秒內知道要做什麼。

## 目前狀態

- **階段**：Phase 3 完成 ✅ → **下一步：Phase 4 謎題模式（或先 Phase 5 發布，見 roadmap 順序備註）**
- **下一個具體動作**：讀 `docs/agent_manual/08_phase4_puzzles.md`，建立 `khet/puzzles.py`
  求解器（AND-OR 搜尋）＋ `scripts/gen_puzzles.py` 生成器；或依使用者意願先走 09 章發布。
- AI 難度實測分級：easy=深度2+噪音 / medium=深度3(0.3s) / hard=深度6上限+5s
  （killer move + 超時部分採用 + 根洗牌 + 重複局面降權——細節與陷阱見手冊 07 章）。

## Phase 總表

| Phase | 內容 | 狀態 | 完成日 |
|---|---|---|---|
| 0 | 規格定案 + 規則查證 + 環境 + 手冊 | ✅ 完成 | 2026-07-04 |
| 1 | 規則引擎 + 測試 | ✅ 完成 | 2026-07-04 |
| 2 | 桌面 GUI（PyQt6） | ✅ 完成 | 2026-07-05 |
| 3 | 對戰 AI | ✅ 完成 | 2026-07-05 |
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
| 2026-07-05 | Phase 3：khet/ai.py（negamax+αβ+TT+迭代加深+killer+超時部分採用）、selfplay.py、GUI 人機對戰（QThreadPool+token 防護）；難度實測定級 2/3/6 | pytest 103 ✅；medium vs random 20/20(100%、0.31s/手) ✅；hard vs medium 7勝2敗1和(70%) ✅ |
| 2026-07-05 | Phase 2：gui/（assets 快取+fallback、對局管理、棋盤+雷射動畫、主視窗）+ main.py；素材 26 張就位並驗證方向；離屏渲染目視驗證（開局/選取/光束/爆閃） | pytest 97 passed ✅（含 GUI offscreen smoke） |
| 2026-07-04 | Phase 1：khet/engine.py + 三個測試檔；AGENT.md 改寫；assets 原始圖改為 gitignore | pytest 94 passed ✅ / 10 萬步 fuzz（100036 plies / 2039 games）✅ / 引擎 0 Qt import ✅ |
| 2026-07-04 | Phase 0：環境 + 規則查證 + 資料檔 + 手冊全套 | validate_layouts ✅ / gen_laser_table 自檢 ✅ / pytest（尚無測試） |
