# 09 Phase 5 — 打磨與桌面發布 v1.0

前置：Phase 2（+建議 Phase 3）完成。里程碑：GitHub Release 上有可下載直接玩的 exe。

## 1. 打磨清單

- [ ] 音效：雷射發射、反射（可選）、命中爆炸、勝利/失敗、按鈕點擊。
      格式 .wav/.ogg，放 `assets/sfx/`；BGM 放 `assets/bgm/`（沿用前作播放架構）。
      沒有現成音源時：可用 ChatGPT/音效生成工具產生，或暫用前作同類音效佔位。
- [ ] 動畫節奏：雷射逐格 30-40ms、命中爆閃 200ms、被吃棋子淡出 150ms；
      提供設定「動畫速度：慢/正常/快/關」。
- [ ] 戰績記錄：勝場數（雙人/對 AI 各難度分開計），JSON 存本機。
- [ ] 正式名稱：**公開發布不可用 "Khet"**。決定名稱前先問使用者
      （README 目前開發代號 Laser Duel）。視窗標題、README、Release 名稱一致。

## 2. PyInstaller 打包

`laser_duel.spec` 要點（參考前作 spec）：

```python
# 重點：datas 要把規則資料與素材帶進去
datas = [
    ("data",   "data"),      # layouts.json / laser_table.json / puzzle_catalog.json
    ("assets", "assets"),    # 棋子/棋盤/特效/UI + sfx/*.wav（音效）
]
```

**打包型態決定（本專案採 onefile）**：使用者要求下載端只有單一 exe，
故 spec 用 `EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, ...)` 且**不使用 COLLECT**
（onedir 會多一包 `_internal/`）。代價：首次啟動稍慢、防毒偶有誤判，但單檔最好散佈。
Windows 圖示必須是 `.ico`（用 pillow 從 app_icon.png 轉，見 requirements.txt 註記）。

打包與驗證：

```powershell
.\venv\Scripts\python.exe -m PyInstaller laser_duel.spec --noconfirm
# 禁止用 pyinstaller.exe wrapper（會靜默失敗）
dist\LaserDuel.exe                    # onefile：單一檔，手動啟動確認可玩
```

注意：程式碼裡讀 `data/` 的路徑要支援 frozen 模式：

```python
import sys, os
ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

（引擎的 `_ROOT` 也要照此調整——這是打包最常見翻車點。）

## 3. Smoke test 套件：`scripts/smoke_test.py`

發布前必跑，全部通過才准 Release：

```
1. 引擎回歸：pytest tests\ -q 全綠
2. GUI 建構：QT_QPA_PLATFORM=offscreen 下建 MainWindow、開新局、走 3 手、存讀檔
3. AI 快速自對戰：medium vs easy 各 2 局跑完無例外
4. 謎題目錄驗證：catalog fingerprint 與抽 3 題重新認證
5.（打包後）dist exe 啟動 → 5 秒內出視窗 → 正常退出（subprocess + timeout）
```

## 4. GitHub Release 流程

```powershell
$gh = "C:\Program Files\GitHub CLI\gh.exe"
# repo 尚未建立時（需使用者同意公開/私有）：
& $gh repo create <name> --private --source . --push
# 打 zip（dist 目錄壓縮，命名 <Name>_v1.0_win64.zip）
Compress-Archive -Path dist\laser_duel\* -DestinationPath dist\LaserDuel_v1.0_win64.zip
& $gh release create v1.0 dist\LaserDuel_v1.0_win64.zip --title "v1.0" --notes "<繁中發布說明>"
```

Release notes 內容：功能清單（雙人/AI 三難度/謎題）、操作說明、系統需求（Win10+）。

## 5. IP 檢查（發布前最後一關）

- [ ] 名稱不含 Khet；介面與文件不出現 Khet 商標（程式碼內部識別字無妨，但對外文字要清）
- [ ] 美術全部是 asset_generation_guide.md 生成的原創科幻機器人主題
- [ ] README 註明「規則啟發自經典雷射棋類遊戲」即可，不要標榜官方授權

## 驗收標準

- [ ] smoke test 5 項全過
- [ ] 乾淨機器（或至少乾淨資料夾）解壓 zip 雙擊 exe 可玩
- [ ] GitHub Release v1.0 上架，README 有下載連結與截圖
