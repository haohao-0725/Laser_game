# Agent 開發手冊 — 導讀（每個 session 必讀，讀我就對了）

本手冊讓任何 AI agent（包括能力較弱的模型）都能把這個雷射棋專案做到發布品質。
**照著做就會對**：所有需要「研究」「查證」「設計決策」的工作都已經完成並寫死在文件裡，
你的工作是實作、串接、跑測試。

## 閱讀協定（防止 context 爆掉的規則）

每個工作 session **只讀這些**，其他章節一律不要讀：

1. 本檔（00_INDEX.md）
2. [01_conventions.md](01_conventions.md) — 座標/方向/朝向/資料格式的唯一定義
3. 專案根目錄的 [PROGRESS.md](../../PROGRESS.md) — 看目前做到哪、這次要做什麼
4. **你當前 Phase 對應的那一章**（見下表）

| 你要做的事 | 讀這章 | 產出物 |
|---|---|---|
| 環境建置 / 第一次接手 | [02_environment.md](02_environment.md) | venv、跑得動測試 |
| 想確認遊戲規則細節 | [03_rules_reference.md](03_rules_reference.md) | （查閱用，非工作章） |
| Phase 1 規則引擎 | [04_phase1_engine.md](04_phase1_engine.md) | `khet/engine.py` 等 |
| Phase 1 測試 | [05_phase1_tests.md](05_phase1_tests.md) | `tests/test_rules.py` 等 |
| Phase 2 桌面 GUI | [06_phase2_gui.md](06_phase2_gui.md) | `gui/` + `main.py` |
| Phase 3 對戰 AI | [07_phase3_ai.md](07_phase3_ai.md) | `khet/ai.py` |
| Phase 4 謎題模式 | [08_phase4_puzzles.md](08_phase4_puzzles.md) | 求解器 + 謎題目錄 |
| Phase 5 打磨與發布 | [09_phase5_release.md](09_phase5_release.md) | exe + GitHub Release |
| Phase 6 手機版 | [10_phase6_mobile.md](10_phase6_mobile.md) | APK |

需要規則以外的背景（美術、IP 注意事項）才去讀 `docs/` 下的其他文件。

## 工作循環（每個 session 都一樣）

```
1. 讀 PROGRESS.md → 確認「下一步」是什麼
2. 讀對應章節 → 章節裡有檔案清單、參考實作、驗收標準
3. 實作（參考實作可以直接抄，抄完要理解介面）
4. 跑測試：.\venv\Scripts\python.exe -m pytest tests\ -q
5. 全綠才算完成。更新 PROGRESS.md（勾掉完成項、寫下一步、記錄異常）
6. 如果使用者要求 commit：訊息用繁中或英文皆可，一個 Phase 內小步提交
```

## 鐵律（違反任何一條 = 你做錯了）

1. **不可手動修改 `data/laser_table.json`**。要改反射規則 → 改 `scripts/gen_laser_table.py` 再重新生成。
2. **不可手動修改 `data/layouts.json` 的數值**。這些是查證過的官方資料。若真要動，
   改完必須跑 `scripts/validate_layouts.py` 且通過。
3. **規則引擎（`khet/` 套件）禁止 import 任何 Qt/GUI 模組**。引擎是純函式層，
   AI、謎題生成器、測試、未來 JS 移植全靠它乾淨。
4. **改了引擎就必須跑全部測試**，紅燈不准往下做。
5. Python 一律用 `.\venv\Scripts\python.exe`（不要用系統 python）。
6. GUI 顯示文字用繁體中文；程式碼 identifier、註解關鍵字用英文。
7. 座標、方向、朝向的定義**只有 01_conventions.md 一個出處**。任何檔案與它矛盾，以它為準，
   並回報矛盾（記到 PROGRESS.md 的「異常記錄」）。
8. 印出中文前先設定編碼（見 02 章），否則 PowerShell 會亂碼。

## 專案一句話

Khet 2.0 類雷射棋數位重製：每回合移動或旋轉一顆棋，然後你的雷射自動發射，
光束被鏡子反射、打中弱點的棋子移除，擊落對方法老（PHARAOH）獲勝。
桌面版 Python 3.10 + PyQt6 → 打包 exe；手機版之後用 Canvas JS + Capacitor，
兩版共用 `data/*.json` 規則資料保證行為一致。
