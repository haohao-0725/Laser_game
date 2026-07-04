# Khet 雷射棋（開發代號：Laser Duel）

雙人雷射棋盤遊戲的數位重製專案：每回合移動或旋轉一顆棋子，然後你的雷射自動發射，
光束經鏡面棋子反射，照到脆弱面的棋子即被移除——擊中對方「王」即獲勝。

靈感來源：Khet 2.0（Mensa Select 得獎作）。本專案為自製學習用重製，
公開發布時將使用原創名稱、美術與題目內容（遊戲規則本身不受著作權保護）。

## 專案狀態

🚧 初始化階段。開發步驟見 [docs/development_roadmap.md](docs/development_roadmap.md)。

## 文件

| 文件 | 內容 |
|---|---|
| [docs/development_roadmap.md](docs/development_roadmap.md) | 開發路線圖（交接文件：未來要做的所有步驟） |
| [docs/rules_spec.md](docs/rules_spec.md) | 實作級規則規格書（引擎開發依據） |
| [docs/asset_generation_guide.md](docs/asset_generation_guide.md) | 美術素材清單與 AI 生圖提示詞（給 ChatGPT 用） |
| [AGENT.md](AGENT.md) | Agent 開發約定（環境、語言、編碼） |

## 技術棧（規劃）

- 桌面版：Python 3.10 + PyQt6，PyInstaller 打包 exe
- 手機版：Web（Canvas）+ Capacitor 打包 APK（沿用 Ricochet Robots 專案已驗證的雙平台管線）
- AI：minimax + alpha-beta 剪枝（迭代加深、走法排序），單人謎題由搜尋反向生成認證
