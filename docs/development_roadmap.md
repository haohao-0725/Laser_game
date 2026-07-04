# 雷射棋開發路線圖（交接文件）

建立日期：2026-07-04
給接手的開發者/Agent：本文件描述從零到雙平台發布的完整步驟。
規則細節見 [rules_spec.md](rules_spec.md)；美術素材見 [asset_generation_guide.md](asset_generation_guide.md)。
前作 Ricochet Robots（`Z:\VScode\Project_Ricochet_Robots`）已驗證的管線與工具盡量沿用。

---

## Phase 0：規格定案（0.5 天）✅ 完成（2026-07-04，僅名稱未定）

- [x] 規則規格書初版（rules_spec.md）
- [x] 對照官方規則補齊【待查證】項目：限制格位置、Sphinx 合法朝向、
      三種初始佈局座標 → 已存成 `data/layouts.json`（查證記錄見 agent_manual/03 §7）
- [x] 雷射真值表 → `data/laser_table.json`（scripts/gen_laser_table.py 生成）
- [x] venv 環境 + requirements.txt + Agent 手冊（docs/agent_manual/，接手必讀）
- [ ] 決定正式名稱與主題（公開發布不可用 "Khet" 名稱與其美術；規則本身無版權問題）
      ——Phase 5 發布前與使用者確認即可

## Phase 1：核心規則引擎（1-2 天）⭐ 一切的地基

- [ ] `laser_rules.py`：LASER_TABLE 資料表（type × orientation × beam_dir → Reflect/Absorb/Hit），
      **存成 JSON** 讓未來 JS 版直接載入同一份表
- [ ] `khet_engine.py`：狀態表示（不可變）、合法行動枚舉（移動/旋轉/換位/限制格）、
      行動套用 + 雷射解算（回傳光束路徑供動畫）、勝負判定
- [ ] `tests/test_rules.py`：
      - 每種棋子 × 每個朝向 × 四方向入射的反射/吸收/摧毀真值表測試
      - 光束多次反射、自傷、Scarab 換位、限制格、Sphinx 不可動等情境
      - 【關鍵】這些測試就是未來手機版的一致性向量來源
- 驗收標準：任意隨機局面 10 萬次隨機走子無例外、無非法狀態

## Phase 2：桌面 GUI（PyQt6，2-3 天）

- [ ] 棋盤渲染（10×8、限制格著色）、棋子渲染（含朝向）、選取 → 移動/旋轉操作
      （建議：點棋子後出現 8 向移動鈕 + 順/逆旋轉鈕，沿用前作的操作習慣）
- [ ] **雷射動畫**：逐格延伸的光束線段 + 反射轉折 + 命中爆閃（本遊戲的靈魂，值得花時間）
- [ ] 本機雙人對戰（hotseat）、悔棋、存讀檔、勝負畫面
- [ ] 沿用前作：BGM/SFX 架構、繁中介面、模式說明對話框
- 里程碑：兩個人可以在同一台電腦完整玩完一局

## Phase 3：對戰 AI（2-4 天）⭐ 新技術樹

- [ ] `khet_ai.py`：minimax + alpha-beta 剪枝
      - 評估函數 v1：子力價值 + 法老周邊安全度 + 「雷射威脅」（下一手可否射到對方要害）
      - 迭代加深 + 走法排序（先試上一層最佳手、吃子手）+ 置換表（Zobrist 雜湊）
      - 分支因子約 60-120，目標深度 4-6 層在 3 秒內
- [ ] 難度分級：深度 2 / 4 / 6 + 評估函數加噪音做出「會犯錯的簡單 AI」
- [ ] AI 對 AI 自動對戰腳本（`scripts/selfplay.py`）：迴歸測試 + 評估函數調參
- 里程碑：中等難度 AI 能穩定擊敗隨機走子 95%+，且體感「有在防守法老」

## Phase 4：單人謎題模式（2-3 天）⭐ 前作技術的移植亮點

市面上所有 Khet 數位版都沒有的功能——用搜尋生成「N 步獲勝」謎題：

- [ ] 謎題求解器：對指定局面做「我方 N 手內必勝（對方任意應手）」的 and-or 搜尋
- [ ] 謎題生成器（前作 endpoint design 思路）：隨機殘局 → 求解器認證「恰好 N 步必勝、
      N-1 步不可行」→ 按 N 分難度帶入目錄（1 步=入門、2 步=中等、3 步=困難）
- [ ] 謎題目錄（JSON，離線認證 + 執行時零等待，沿用前作 map_catalog 模式）
- 里程碑：17 題 × 3 難度的認證謎題目錄，「每日一題」介面

## Phase 5：打磨與桌面發布（1-2 天）

- [ ] 音效（雷射聲、命中聲、勝利聲）、動畫節奏調整、紀錄（勝場數）
- [ ] PyInstaller spec + exe 打包（`python -m PyInstaller`，不用 wrapper）
- [ ] GitHub repo + Release v1.0（exe + zip；gh 在 `"C:\Program Files\GitHub CLI\gh.exe"`）
- [ ] smoke test 套件（offscreen GUI 建構 + 引擎回歸 + AI 快速自對戰）

## Phase 6：手機版（Capacitor，2-3 天）

沿用前作已驗證的整套管線（見前作 memory / AGENT）：

- [ ] `www/` Canvas 版：game.js 移植引擎（LASER_TABLE 直接載入同一份 JSON）
- [ ] 【必做】規則一致性向量測試：Python 生成 400+ 隨機（局面, 行動）→ 結果 JSON，
      瀏覽器端逐一比對（前作 chaos 模式做過 400/400，照抄流程）
- [ ] AI 移植：JS minimax（深度調低）或 WebWorker 跑
- [ ] `npx cap sync android` + gradlew assembleDebug（E:\ 環境，呼叫方式見 AGENT.md）
- 里程碑：APK 可玩、雙平台規則零差異

## Phase 7：進階（可選，之後再說）

- 線上對戰（WebSocket）、MCTS/更強 AI、開局庫、棋譜記錄/重播、
  自訂佈局編輯器（沿用前作 wall_editor 思路）、ELO 排名

---

## 風險與注意事項

1. **IP**：公開發布前改名換美術（美術由 asset_generation_guide.md 生成原創素材解決）。
   自用/學習階段無虞。
2. **AI 強度 vs Python 效能**：深度 6 若太慢，優先做走法排序與置換表，
   再考慮 bitboard 化（前作 session_planner 的位棋盤經驗可借用）；別急著換語言。
3. **雷射表正確性是一切根基**：LASER_TABLE 寫錯會污染引擎、AI、謎題全部下游，
   Phase 1 的真值表測試必須先行、必須完整。
4. **雙平台一致性**：規則表共用 JSON + 隨機向量比對，兩道保險都要做。

## 建議開發順序總覽

```
P0 規格 → P1 引擎+測試 → P2 GUI（先能玩）→ P3 AI（先能單機玩）
→ P5 桌面發布 v1.0 → P4 謎題模式 → v1.1 → P6 手機版 → v1.2
```

（P4 與 P5 可對調：先發布純對戰版收集手感回饋，謎題模式當 v1.1 亮點。）
