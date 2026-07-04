# Khet 雷射棋 Agent 說明

## 用途

此 repository 是雷射棋（Khet 類）的數位重製專案：核心規則引擎、雷射解算、
對戰 AI（minimax/alpha-beta）、單人謎題生成、PyQt6 GUI 與之後的 Capacitor 手機版。

在此 repo 中工作時，請優先遵守以下原則：

- 規則引擎與 GUI 分離：`rules` 層為純函式（無 Qt 依賴），可被 AI、謎題生成器與測試直接重用
- 不把 exe、zip、build cache、虛擬環境或大型開發素材提交到 Git
- GUI 顯示文字使用繁體中文；程式碼 identifier 維持英文
- 變更規則引擎後必須跑 `tests\`（尤其是雷射解算的規則向量測試）
- 之後移植手機版時，以「隨機狀態向量比對」驗證 Python 與 JS 規則一致性
  （參考 Ricochet Robots 專案 chaos 模式的 400 向量作法）

## 語言使用說明

和使用者溝通、撰寫 README / AGENT / 專案說明時，使用繁體中文。
程式碼 identifier 維持英文；註解只在有助於理解複雜邏輯時加入。

## 執行環境

### Python 環境

使用 **Python 3.10** 與本機 venv。全新 clone 後：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

執行 Python 一律使用 `.\venv\Scripts\python.exe`。
打包使用 `python -m PyInstaller <spec>`（不要用 pyinstaller.exe wrapper，會靜默失敗）。

### 中文字元編碼

PowerShell 中執行會輸出中文的腳本前：

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 相關工具路徑（本機）

- GitHub CLI：`"C:\Program Files\GitHub CLI\gh.exe"`（不在 PATH 上）
- Android 建置環境：E:\（見 `Z:\VScode\_FOR_agent_common_information\android-studio-environment.md`）
- gradle 呼叫方式：`cmd /c "cd /d <android目錄> && .\gradlew.bat assembleDebug --no-daemon"`

## 參考專案

`Z:\VScode\Project_Ricochet_Robots`（桌面）與 `Z:\VScode\Ricochet_Robots_Mobile`（手機）
是同作者的前作，以下模式直接沿用：

- 離線認證目錄 + 執行時零等待載入
- 反向建構生成認證關卡（endpoint design，見前作 `docs/endpoint_inverse_design.md`）
- PyInstaller exe + GitHub Release 發布流程
- Capacitor 手機版移植與規則一致性向量測試
