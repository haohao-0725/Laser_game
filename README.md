# Khet 雷射棋（開發代號：Laser Duel）

雙人雷射棋盤遊戲的數位重製專案：每回合移動或旋轉一顆棋子，然後你的雷射自動發射，
光束經鏡面棋子反射，照到脆弱面的棋子即被移除——擊中對方「王」即獲勝。

靈感來源：Khet 2.0（Mensa Select 得獎作）。本專案為自製學習用重製，
公開發布時將使用原創名稱、美術與題目內容（遊戲規則本身不受著作權保護）。

## 專案狀態

✅ **桌面版 v1.0 完成**：核心規則引擎、PyQt6 GUI（雙人對戰、雷射動畫、悔棋、存讀檔）、
對戰 AI（三難度）、單人謎題模式（39 題認證目錄 + 每日一題）、音效與戰績、PyInstaller 打包。
下一步為 Phase 6 手機版。目前進度見 [PROGRESS.md](PROGRESS.md)。

## 執行與打包

```powershell
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py                                   # 執行
.\venv\Scripts\python.exe -m pytest tests\ -q                       # 測試
.\venv\Scripts\python.exe -m PyInstaller laser_duel.spec --noconfirm  # 打包 exe
```

## 功能

- **雙人對戰**（同機輪流）＋ 三種官方佈局（經典／印和闐／王朝）
- **人機對戰**：AI 三難度（簡單／中等／困難），背景執行緒思考不卡介面
- **謎題模式**：39 題「N 手必勝」認證謎題（1–3 手）＋ 每日一題＋提示
- 逐格雷射動畫、悔棋、存讀檔、音效開關、戰績記錄

## 文件

| 文件 | 內容 |
|---|---|
| [PROGRESS.md](PROGRESS.md) | **進度儀表板**（接手先看這個） |
| [docs/agent_manual/00_INDEX.md](docs/agent_manual/00_INDEX.md) | **Agent 開發手冊導讀**（各 Phase 完整參考實作與驗收標準） |
| [docs/development_roadmap.md](docs/development_roadmap.md) | 開發路線圖（高層規劃） |
| [docs/rules_spec.md](docs/rules_spec.md) | 實作級規則規格書（已查證版） |
| [docs/asset_generation_guide.md](docs/asset_generation_guide.md) | 美術素材清單與 AI 生圖提示詞（給 ChatGPT 用） |
| [AGENT.md](AGENT.md) | Agent 開發約定（環境、語言、編碼） |

## 權威規則資料（雙平台共用）

- `data/layouts.json` — 三種官方佈局、限制格、Sphinx 定義（已查證，勿手改）
- `data/laser_table.json` — 雷射互動真值表（由 `scripts/gen_laser_table.py` 生成，勿手改）

## 技術棧（規劃）

- 桌面版：Python 3.10 + PyQt6，PyInstaller 打包 exe
- 手機版：Web（Canvas）+ Capacitor 打包 APK（沿用 Ricochet Robots 專案已驗證的雙平台管線）
- AI：minimax + alpha-beta 剪枝（迭代加深、走法排序），單人謎題由搜尋反向生成認證
