# 01 慣例與資料格式（唯一權威定義，全專案通用）

任何程式碼、文件、測試與本章矛盾時，**以本章為準**。

## 1. 座標系

- 棋盤 10 欄 × 8 列。`col` ∈ 0..9（左→右）、`row` ∈ 0..7（上→下，螢幕座標習慣）。
- 人類記法（僅用於文件與除錯輸出）：欄 a-j = col 0-9，rank 8-1 = row 0-7。
  即 `a8 = (col 0, row 0)` 左上角、`j1 = (col 9, row 7)` 右下角。
- **紅方（RED）在上方**（row 0 是紅方底線），**銀方（SILVER）在下方**（row 7 是銀方底線）。
- 換算函式：`cell_name(col, row) = "abcdefghij"[col] + str(8 - row)`。

## 2. 方向（direction）

光束行進方向與移動方向共用同一套編號：

| 值 | 名稱 | 座標變化 |
|---|---|---|
| 0 | N | row - 1 |
| 1 | E | col + 1 |
| 2 | S | row + 1 |
| 3 | W | col - 1 |

- `opposite(d) = (d + 2) % 4`；順時針旋轉一步 = `(d + 1) % 4`。
- 8 方向移動用 (dcol, drow) 向量表：
  `MOVE_VECTORS = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]`（N 開始順時針）。

## 3. 棋子類型與朝向（orientation）

每顆棋子 = `(type, color, col, row, orientation)`，orientation ∈ {0,1,2,3}。

| type | 中文/官方名 | 每方數量 | 雷射互動 | orientation 意義 |
|---|---|---|---|---|
| `PHARAOH` | 法老（王） | 1 | 任何面被打中 → 移除，該方輸 | 無意義，一律 0 |
| `SPHINX` | 獅身人面（雷射砲台） | 1 | 任何面 → 吸收（免疫） | **砲口方向**。紅方固定在 a8，只能朝 1(E) 或 2(S)；銀方固定在 j1，只能朝 0(N) 或 3(W) |
| `PYRAMID` | 金字塔（單面鏡） | 7 | 鏡面 → 90° 反射；另兩面 → 移除 | k 表示**鏡面朝向 {方位k, 方位k+1}**：0={N,E}、1={E,S}、2={S,W}、3={W,N}。幾何上 0/2 是 `\` 對角線、1/3 是 `/` |
| `SCARAB` | 聖甲蟲（雙面鏡） | 2 | 兩面都反射，**不可能被移除** | 0 = `\`（NW-SE 對角線）、1 = `/`。2、3 合法但與 0、1 等價（引擎以 `% 2` 正規化） |
| `ANUBIS` | 阿努比斯（盾衛） | 2 | 正面（盾面）→ 吸收無事；側/背面 → 移除 | **盾牌面朝向**（0=N 朝上） |

反射結果一律查 `data/laser_table.json`：`table[type][orientation][beam_dir]`
→ `{"result":"reflect","dir":新方向}` / `{"result":"absorb"}` / `{"result":"hit"}`。
`beam_dir` 是**光束行進方向**（不是來向）。

記憶輔助：PYRAMID orientation 0（鏡面朝 N+E）：從北面來的光（行進方向 S）反射向 E；
從東面來的光（行進方向 W）反射向 N；光束行進方向為 N 或 E 時打中的是背面 → 移除。

## 4. 限制格（restricted squares）

只有該色棋子能「進入或停留」的格子（含 Scarab 換位：不可把對方棋子換進對方不可停留的格）：

- 紅方專用（10 格）：整個 a 欄（col 0 全部 8 格，含 a8）＋ `i8`(8,0) ＋ `i1`(8,7)
- 銀方專用（10 格）：整個 j 欄（col 9 全部 8 格，含 j1）＋ `b8`(1,0) ＋ `b1`(1,7)

a8 / j1 同時是 Sphinx 固定座（Sphinx 永不移動、永不被移除，所以不需要額外規則）。
權威資料在 `data/layouts.json` 的 `restricted` 欄位，引擎直接載入，不要在程式裡硬編。

## 5. 行動（Action）表示

```python
Move(col, row, dcol, drow)      # 移到相鄰空格（8 方向）
Swap(col, row, dcol, drow)      # 僅 SCARAB：與相鄰 PYRAMID/ANUBIS（不分敵我）交換
Rotate(col, row, cw)            # 原地旋轉 90°，cw=True 順時針；SPHINX 只能在合法朝向間切換
```

回合流程：選一個行動 → 執行 → **自己的 Sphinx 強制發射雷射** → 結算移除 → 檢查勝負 → 換人。
銀方先手（`layouts.json` 的 `first_player`）。

## 6. 狀態（State）表示

不可變（immutable）：`state = (current_player, pieces)`，
`pieces` 是排序過的 tuple，每個元素 `(type, color, col, row, orientation)`（全部字串/整數）。
排序保證同局面必得同一個 tuple → 可直接當 dict key / 雜湊（AI 置換表、三次同形偵測都靠這個）。

## 7. 檔案地圖（最終狀態）

```
Khet_game/
├── data/
│   ├── layouts.json        # 佈局+限制格+Sphinx 定義（已查證，勿改）
│   └── laser_table.json    # 雷射真值表（生成物，勿手改）
├── khet/                   # 純規則層（無 Qt！）
│   ├── __init__.py
│   ├── engine.py           # 狀態、合法行動、雷射解算、勝負
│   ├── ai.py               # minimax AI（Phase 3）
│   └── puzzles.py          # 謎題求解/生成（Phase 4）
├── gui/                    # PyQt6 介面（Phase 2）
├── tests/                  # pytest（隨引擎成長）
├── scripts/                # 生成器、selfplay、工具
├── assets/                 # 美術素材（見 docs/asset_generation_guide.md）
├── main.py                 # GUI 入口
└── www/                    # Phase 6 手機版 Canvas 網頁
```

## 8. 程式碼慣例

- Python 3.10、4 空格縮排、識別字英文；註解精簡、只解釋「為什麼」。
- 引擎層純函式 + 標準函式庫，回傳新狀態而非原地修改。
- GUI 文字繁體中文。錯誤訊息與 log 也用繁中。
- 測試命名 `test_<主題>_<情境>`；每個 bug 修復都要先加會紅的測試。

## 9. 術語對照（讀外部資料時用）

| 本專案 | Khet 官方 | Laser Chess (ThinkFun) |
|---|---|---|
| PHARAOH | Pharaoh | King |
| SPHINX | Sphinx | Laser |
| PYRAMID | Pyramid | Deflector |
| SCARAB | Scarab | Switch |
| ANUBIS | Anubis | Defender |
| SILVER | Silver（先手） | Blue（先手） |
