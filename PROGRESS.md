# 專案進度儀表板（每個 session 結束前更新這裡）

> 使用方式見 `docs/agent_manual/00_INDEX.md`。原則：這個檔案永遠反映**現在的真實狀態**，
> 讓下一個接手的 agent 30 秒內知道要做什麼。

## 目前狀態

- **階段**：Phase 0–7A 完成 ✅ 桌面版 AI v2／v1.1.0 已完成；手機版維持 v1.0。
- **可能的後續（Phase 7 選配）**：線上對戰、棋譜重播、自訂佈局編輯器、ELO、
  AI 認證平衡開局庫。手機版 AI v2／三次同形同步此次依使用者指示暫不維護。
- **重生手機版建置的方法**（android/ 是 gitignore）：
  1. `npm install`
  2. `.\venv\Scripts\python.exe scripts\export_web_data.py`（規則改過才需要）
  3. `npx cap add android`（若無 android/）→ `npx cap sync android`
  4. `cmd /c "cd /d <root>\android && .\gradlew.bat assembleDebug --no-daemon"`
     （環境變數見 AGENT.md；產物 android\app\build\outputs\apk\debug\app-debug.apk）

## Phase 總表

| Phase | 內容 | 狀態 | 完成日 |
|---|---|---|---|
| 0 | 規格定案 + 規則查證 + 環境 + 手冊 | ✅ 完成 | 2026-07-04 |
| 1 | 規則引擎 + 測試 | ✅ 完成 | 2026-07-04 |
| 2 | 桌面 GUI（PyQt6） | ✅ 完成 | 2026-07-05 |
| 3 | 對戰 AI | ✅ 完成 | 2026-07-05 |
| 4 | 謎題模式 | ✅ 完成 | 2026-07-05 |
| 5 | 打磨 + 桌面發布 v1.0 | ✅ 完成 | 2026-07-05 |
| 6 | 手機版 APK | ✅ 完成 | 2026-07-06 |
| 7A | 桌面 AI v2（和局搜尋、PVS、戰術／局面評估） | ✅ 完成 | 2026-07-16 |

（Phase 4 與 5 順序可對調，見 roadmap。正式名稱未定，發布前要問使用者。）

## 已完成的地基（Phase 0，2026-07-04）

- venv 建立（Python 3.10.8 + PyQt6 6.7.1 + pytest 8.3.3 + pyinstaller，鎖版 requirements.txt）
- 規則三項【待查證】全部查證完畢（限制格/Sphinx/三種佈局），來源與方法見手冊 03 章 §7
- `data/layouts.json`（權威佈局資料）＋ `scripts/validate_layouts.py`（驗證通過）
- `data/laser_table.json`（由 `scripts/gen_laser_table.py` 生成，內建自檢通過）
- Agent 手冊 `docs/agent_manual/00-10` 全套

## 異常記錄（發現文件矛盾、規則疑義、環境問題都記在這）

- 手機版仍是 v1.0：尚未同步桌面 AI v2，也尚未加入三次同形對局終局；這是本次明確保留的版本差異。

## Session 日誌（最新在上，一行一 session）

| 日期 | 做了什麼 | 測試狀態 |
|---|---|---|
| 2026-07-16 | Phase 7A：桌面 AI v2（搜尋樹三次同形、repetition-aware TT、PVS/aspiration/history、選擇性 quiescence、戰術排序、光路/機動性/法老安全評估）；桌面和局後鎖定落子；selfplay 分開正式和局與手數上限 | pytest 116 ✅；medium vs random 20/20（0.2s/手）✅；v2 vs v1 3勝0敗1截斷（交換先後手）✅；桌面打包/Release v1.1.0 ✅ |
| 2026-07-06 | Phase 6：www/ Canvas 手機版（engine.js/ai.js/game.js 移植 + 觸控 UI）、export_web_data.py、規則一致性向量測試、Capacitor + APK 建置成功（25.8MB） | pytest 111 ✅（含 web 一致性）；向量 500/500 PASS ✅；瀏覽器實測互動/AI/動畫 ✅；APK BUILD SUCCESSFUL ✅ |
| 2026-07-05 | Phase 4+5：謎題求解器/生成器（39 題認證目錄）、謎題 GUI+每日一題、音效合成、設定/戰績持久化、PyInstaller 打包、smoke test、發布到 GitHub | pytest 110 ✅；目錄 39 題認證 ✅；smoke test 4 項 ✅；exe 啟動驗證 ✅ |
| 2026-07-05 | Phase 3：khet/ai.py（negamax+αβ+TT+迭代加深+killer+超時部分採用）、selfplay.py、GUI 人機對戰（QThreadPool+token 防護）；難度實測定級 2/3/6 | pytest 103 ✅；medium vs random 20/20(100%、0.31s/手) ✅；hard vs medium 7勝2敗1和(70%) ✅ |
| 2026-07-05 | Phase 2：gui/（assets 快取+fallback、對局管理、棋盤+雷射動畫、主視窗）+ main.py；素材 26 張就位並驗證方向；離屏渲染目視驗證（開局/選取/光束/爆閃） | pytest 97 passed ✅（含 GUI offscreen smoke） |
| 2026-07-04 | Phase 1：khet/engine.py + 三個測試檔；AGENT.md 改寫；assets 原始圖改為 gitignore | pytest 94 passed ✅ / 10 萬步 fuzz（100036 plies / 2039 games）✅ / 引擎 0 Qt import ✅ |
| 2026-07-04 | Phase 0：環境 + 規則查證 + 資料檔 + 手冊全套 | validate_layouts ✅ / gen_laser_table 自檢 ✅ / pytest（尚無測試） |
