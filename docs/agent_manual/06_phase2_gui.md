# 06 Phase 2 — 桌面 GUI（PyQt6）

前置：Phase 1 全綠。產出物：`gui/` 套件 + `main.py`。
里程碑：兩個人可以在同一台電腦hotseat完整玩完一局，含雷射動畫、悔棋、存讀檔。

## 檔案結構

```
main.py                  # 入口：QApplication + MainWindow
gui/
├── __init__.py
├── main_window.py       # 選單（新局/佈局選擇/存讀檔/說明）、狀態列
├── board_widget.py      # 棋盤繪製 + 滑鼠互動 + 雷射動畫（本章重點）
├── game_controller.py   # 對局狀態機：歷史堆疊(悔棋)、三次同形偵測、存讀檔
└── assets.py            # QPixmap 載入與快取（棋子/棋盤/特效）
```

GUI 只透過 `khet` 套件的公開介面操作遊戲；**GUI 檔案裡不准出現規則邏輯**
（例如不准自己判斷反射方向——一切問引擎）。

## 繪製規格

- 視窗基準 1280×800，可縮放；棋盤區維持 10:8 比例置中，格子大小 = min(可用寬/10, 可用高/8)。
- 圖層順序：棋盤底圖 → 格線 → 限制格著色（紅格淡紅、銀格淡青，用半透明疊色）
  → 棋子 → 選取高亮 → 行動按鈕 → 雷射光束 → 命中特效。
- 棋子圖檔（見 docs/asset_generation_guide.md 檔名表）**預設朝向為 N（朝上）**。
  繪製時旋轉角度 = `orientation * 90` 度（順時針）：
  - SPHINX/ANUBIS：直接轉 orientation × 90°。
  - PYRAMID：素材規格（asset guide §1.3）是鏡面在 NW-SE 對角線、機體佔左下半，
    即裝甲面朝 W 和 S、鏡面朝 {N,E} = orientation 0 的樣子。所以同樣直接轉 orientation × 90°。
  - SCARAB：素材是 NW-SE 斜置刀鋒 = orientation 0（`\`）；orientation 1 轉 90°。
- 素材還沒生成前，**先用 QPainter 幾何圖形畫佔位棋子**（三角形＋粗斜線標鏡面、
  盾形標 ANUBIS 正面、圓形 PHARAOH、砲管 SPHINX），確保方向資訊清楚。
  不要因為等素材卡住開發。

## 互動狀態機（沿用前作操作習慣）

```
IDLE：點自己的棋 → SELECTED（高亮 + 顯示行動鈕）
SELECTED：
  - 8 個方向鈕（僅合法方向顯示；SCARAB 換位目標顯示交換圖示）
  - 順/逆旋轉鈕（依 legal_actions 過濾；SPHINX 只顯示一顆「切換朝向」鈕）
  - 點其他自己的棋 → 改選；點空白處 → 取消
  - 點行動鈕 → ANIMATING
ANIMATING（雷射動畫播放中，輸入鎖定）：
  - 動畫完 → 若有棋被移除播爆閃 → 檢查勝負 → 換人 → IDLE / GAME_OVER
```

行動鈕實作提示：在 board_widget 上以浮動 QPushButton 或自繪 hit-region 皆可；
前作 Ricochet Robots 的做法是自繪圖示 + 座標命中測試，比較好控制縮放。

## 雷射動畫（本遊戲的靈魂，值得花時間）

`apply_action` 回傳的 `LaserResult.path` 是光束經過的每一格。動畫做法：

1. `QTimer` 每 30-40ms 推進一格，畫「已經過線段」＋當前前緣亮點。
2. 線段畫法：相鄰兩格中心連線，`QPen` 粗 4-6px、亮紅橙色、外圈再畫一層半透明寬線做光暈。
3. 轉折格（path 中方向改變的點）畫一個小十字閃光。
4. 終點事件：`hit` → 爆閃（放大圓 + 淡出，200ms）後移除棋子圖；`absorb` → 小盾光；
   `exit` → 前緣飛出棋盤淡出。
5. 動畫總長控制在 1.2 秒內；提供「動畫速度」設定（快/慢/關）。

## game_controller.py 規格

```python
class GameController:
    def __init__(self, layout: str = "classic")
    # 狀態
    state: tuple                     # 目前引擎狀態
    history: list[tuple]             # 歷代 state（悔棋用，悔一次退「一整手」）
    position_counts: dict[tuple, int]  # 三次同形：state -> 出現次數
    # 操作
    def do_action(self, action) -> LaserResult   # 呼叫引擎、推歷史、更新同形計數
    def undo(self) -> bool                        # 退一手（雙人模式退 1 手、對 AI 退 2 手）
    def is_draw_by_repetition(self) -> bool       # 某 state 出現第 3 次
    def save(self, path)  /  def load(self, path) # JSON：layout + action 序列（重放式存檔）
```

存檔格式用「action 序列重放」而非快照——檔案小、天然相容悔棋歷史，
載入時逐步 `apply_action` 重建（引擎快，80 手內毫秒級）。

## 其他必做

- 新局對話框：選佈局（classic/imhotep/dynasty，各附縮圖或文字說明）。
- 勝負畫面：顯示贏家 + 「再來一局」；三次同形顯示和局。
- 模式說明對話框（規則簡介，繁中，可抄 03 章 §2-§3 改寫成玩家語言）。
- BGM/SFX 架構與繁中介面慣例沿用前作（`Z:\VScode\Project_Ricochet_Robots` 的 gui 層）；
  音效檔 Phase 5 才補，先留 `play_sound(name)` 空殼。
- 視窗 icon 用 `assets/app_icon.png`（沒有就先略過）。

## 驗收標準

- [ ] hotseat 完整玩完一局（含勝負畫面）
- [ ] 雷射動畫逐格延伸、轉折、命中爆閃皆正確對應 `LaserResult.path`
- [ ] 悔棋、存檔、讀檔、三次同形和局皆可用
- [ ] `pytest` 全綠（GUI 加一個 smoke test：offscreen 模式建構 MainWindow 不炸，
      `QT_QPA_PLATFORM=offscreen` 環境變數）
- [ ] 引擎層仍然 0 個 Qt import
