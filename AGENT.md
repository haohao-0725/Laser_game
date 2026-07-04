# AGENT.md — 本專案的 Agent 運作規則（接手第一份必讀文件）

此 repository 是雷射棋（Khet 2.0 類）數位重製專案：核心規則引擎、雷射解算、
對戰 AI（minimax/alpha-beta）、單人謎題生成、PyQt6 桌面版與後續 Capacitor 手機版。

## 接手流程（照順序，不要跳步）

1. 讀本檔（就是現在）
2. 讀 [PROGRESS.md](PROGRESS.md) → 知道目前進度與「下一步」
3. 讀 [docs/agent_manual/00_INDEX.md](docs/agent_manual/00_INDEX.md) → 手冊導讀與閱讀協定
4. 讀 [docs/agent_manual/01_conventions.md](docs/agent_manual/01_conventions.md) → 座標/方向/朝向唯一定義
5. 只再讀「當前 Phase 對應的那一章」，開始工作
6. 每個 session 結束前更新 PROGRESS.md（完成項、下一步、異常記錄）

手冊各章含**完整參考實作與驗收標準**，照著做即可；禁止自行重新設計已定案的架構。

## 鐵律（違反任何一條 = 做錯了）

1. `data/laser_table.json` 禁止手改——要改就改 `scripts/gen_laser_table.py` 重新生成。
2. `data/layouts.json` 是查證過的官方資料，禁止改數值；動過必跑
   `scripts/validate_layouts.py` 且通過。
3. `khet/` 規則層是純函式，**禁止 import 任何 Qt/GUI 模組**；GUI 檔案裡禁止出現規則邏輯。
4. 改了引擎必跑 `.\venv\Scripts\python.exe -m pytest tests\ -q`，紅燈不准往下做。
5. Python 一律用 `.\venv\Scripts\python.exe`（專案 venv，不碰系統 Python）。
6. 文件與 GUI 文字用繁體中文；程式碼 identifier 用英文；註解只解釋「為什麼」。
7. 慣例定義只有 `01_conventions.md` 一個出處，發現矛盾以它為準並記入 PROGRESS.md。
8. 不把 exe、zip、build cache、venv、大型素材提交進 Git。
9. 沒有使用者指示不要 push、不要發 Release、不要改遊戲正式名稱。

## 美術素材狀態（重要）

`assets/` 的圖片**由使用者親自生成中，尚未就位**。在使用者放入檔案之前：

- 程式**不要讀取 assets/ 的圖片**；GUI 一律用 QPainter 幾何佔位圖形
  （方向資訊必須清楚：鏡面斜線、盾面、砲口）。
- 檔名規範以 `docs/asset_generation_guide.md` §7 的檔名總表為準；
  之後接素材時寫成「檔案存在就用圖、不存在就 fallback 佔位圖形」，兩者可隨時切換。

## 執行環境

### Python

Python 3.10 + 專案 venv。全新 clone 後：

```powershell
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

打包用 `python -m PyInstaller <spec>`（**不要用** pyinstaller.exe wrapper，會靜默失敗）。

### 中文輸出前先設編碼

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 本機工具路徑

- GitHub CLI：`"C:\Program Files\GitHub CLI\gh.exe"`（不在 PATH）
- Android 建置環境：E:\（見 `Z:\VScode\_FOR_agent_common_information\android-studio-environment.md`）
- gradle：`cmd /c "cd /d <android目錄> && .\gradlew.bat assembleDebug --no-daemon"`

## Git 慣例

- 一個 Phase 內小步提交；訊息格式 `Phase N: <做了什麼>`（繁中或英文皆可）。
- 生成物中只有 `data/laser_table.json`（與之後的 `data/puzzle_catalog.json`）要提交。

## 參考專案（同作者前作，管線直接沿用）

- 桌面版：`Z:\VScode\Project_Ricochet_Robots`（PyInstaller/GUI/音效架構）
- 手機版：`Z:\VScode\Ricochet_Robots_Mobile`（Capacitor/規則一致性向量測試）
