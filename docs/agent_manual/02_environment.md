# 02 環境建置與工具（第一次接手先讀這章）

## Python 環境（隔離 venv，不碰系統 Python）

專案根目錄應已存在 `venv\`（Python 3.10.8）。若不存在（例如全新 clone）：

```powershell
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

**之後所有 Python 執行一律走 `.\venv\Scripts\python.exe`**，例如：

```powershell
.\venv\Scripts\python.exe -m pytest tests\ -q          # 跑測試
.\venv\Scripts\python.exe main.py                       # 跑 GUI
.\venv\Scripts\python.exe scripts\gen_laser_table.py    # 重生雷射表
```

已安裝套件：PyQt6 6.7.1、pytest 8.3.3、pyinstaller 6.11.1（版本鎖在 requirements.txt）。
新增依賴時：裝進 venv、**同步更新 requirements.txt（鎖版本）**。

## PowerShell 中文編碼（每次要輸出中文前先執行）

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

寫檔案時 Python 端一律 `open(path, encoding="utf-8")`；
PowerShell 寫檔要加 `-Encoding utf8`。

## 驗證環境是否正常（接手後先跑一次）

```powershell
.\venv\Scripts\python.exe -c "import PyQt6.QtCore; print(PyQt6.QtCore.PYQT_VERSION_STR)"
.\venv\Scripts\python.exe scripts\validate_layouts.py
.\venv\Scripts\python.exe -m pytest tests\ -q
```

三個都成功 = 環境 OK。pytest 若顯示「no tests ran」代表還在 Phase 1 之前，正常。

## 本機工具路徑

| 工具 | 路徑/呼叫方式 |
|---|---|
| GitHub CLI | `& "C:\Program Files\GitHub CLI\gh.exe"`（不在 PATH） |
| PyInstaller | `.\venv\Scripts\python.exe -m PyInstaller <spec>`（**禁用** pyinstaller.exe wrapper，會靜默失敗） |
| Android 建置 | E:\ 磁碟環境，說明見 `Z:\VScode\_FOR_agent_common_information\android-studio-environment.md` |
| gradle | `cmd /c "cd /d <android目錄> && .\gradlew.bat assembleDebug --no-daemon"` |

## Git 紀律

- `venv/`、`build/`、`dist/`、`__pycache__/`、`*.zip` 已在 .gitignore，**不准提交**。
- 生成物中只有 `data/laser_table.json` 要提交（它是跨平台規則的共用資產）。
- 沒有使用者指示不要 push、不要開 Release。

## 參考前作（僅在對應 Phase 需要時查閱）

- 桌面版管線參考：`Z:\VScode\Project_Ricochet_Robots`
- 手機版管線參考：`Z:\VScode\Ricochet_Robots_Mobile`
