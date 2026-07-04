# 10 Phase 6 — 手機版（Canvas JS + Capacitor）

前置：桌面 v1.0 發布。里程碑：APK 可玩、**雙平台規則零差異**（有向量測試證明）。
整套管線前作已驗證，遇到不確定的建置問題先看：
`Z:\VScode\Ricochet_Robots_Mobile`（成品參考）與
`Z:\VScode\_FOR_agent_common_information\android-studio-environment.md`（環境）。

## 1. `www/` 結構（純靜態，先在桌面瀏覽器開發）

```
www/
├── index.html
├── css/style.css
├── js/
│   ├── rules_data.js     # 由腳本從 data/*.json 生成：window.LASER_TABLE = {...} 等
│   ├── engine.js         # khet/engine.py 的逐函式移植
│   ├── ai.js             # minimax（深度調低到 3-4，或 WebWorker 跑 4-5）
│   ├── game.js           # Canvas 渲染 + 觸控互動 + 動畫
│   └── vectors_test.js   # 一致性向量測試執行器（開發用頁面掛載）
└── assets/               # 縮圖化素材（棋子 256px 即可）
```

規則資料**不要手寫 JS 版**：寫 `scripts/export_web_data.py` 把
`data/laser_table.json`、`data/layouts.json`、`data/puzzle_catalog.json`
包成 `rules_data.js`（`window.X = <json>;`），單一來源保持不變。

## 2. engine.js 移植規則

- 函式名、參數、回傳結構與 Python 版一一對應（`legal_actions`、`apply_action`...），
  state 用 `{player, pieces:[[type,color,col,row,ori],...]}`，pieces 排序規則與 Python
  `sorted()` 對 tuple 的字典序一致（先 type 字串、再 color、再 col...）。
  **排序一致很重要**：向量比對會直接比序列化結果。
- 移植完先跑向量測試再寫 UI。

## 3. 【必做】規則一致性向量測試

```
1. Python 端：scripts/gen_test_vectors.py
   - 從三種佈局出發，隨機走子產生 400+ 筆 (state, action) → 執行 apply_action
   - 輸出 vectors.json：[{state_in, action, state_out, laser_path, event}, ...]
2. JS 端：vectors_test.js 逐筆執行 engine.js 的 apply_action，
   比對 state_out / laser_path / event 完全一致，頁面顯示「400/400 PASS」
3. 不到 400/400 不准進下一步（前作 chaos 模式同流程，做過 400/400）
```

## 4. 觸控 UI 要點

- 直式手機佈局：棋盤在上（滿寬，10:8）、下方控制列（選中棋子的行動鈕放大顯示）。
- 點棋子 → 高亮 + 下方出現方向/旋轉大按鈕（手指目標 ≥ 44px）。
- 雷射動畫與桌面同節奏；requestAnimationFrame 實作。
- 對 AI 模式：AI 在 WebWorker 算，主執行緒不卡。

## 5. Capacitor 打包

```powershell
# www/ 完成並通過向量測試後（Node 專案初始化參考前作 package.json）
npx cap init   # 已 init 過則略
npx cap sync android
cmd /c "cd /d <android平台目錄> && .\gradlew.bat assembleDebug --no-daemon"
# 環境細節（SDK 路徑、簽章、E:\ 磁碟）見 android-studio-environment.md
```

APK 裝機測試清單：觸控選子/走子/旋轉、雷射動畫流暢、AI 對戰、謎題模式、
橫豎屏（鎖直式即可）、返回鍵行為。

## 驗收標準

- [ ] 向量測試 400/400 PASS（截圖或 log 記到 PROGRESS.md）
- [ ] APK 在實機可完整玩一局（雙人 + AI）
- [ ] 桌面瀏覽器版與 APK 行為一致
- [ ] （可選）Release 附上 APK
