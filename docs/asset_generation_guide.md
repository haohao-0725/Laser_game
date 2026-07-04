# 美術素材生成指南（給 ChatGPT / AI 生圖工具）

本文件列出雷射棋需要的**全部**圖片素材：每項有檔名、用途、規格與可直接複製的英文提示詞。
生成後放入 `assets/`，依「檔名規範」命名。

## 0. 整體美術方向（重要：先讀這段再開始生圖）

**主題：科幻機器人雷射戰**（不使用 Khet 的埃及主題與美術，避免版權問題；
也和前作 Ricochet Robots 的機器人品牌形象一致）。

**所有棋子共通規格**：
- 尺寸 1024×1024、**PNG 透明背景**、正上方俯視角（top-down）——這是棋盤遊戲，不要透視角
- 同一棋子做**兩個配色**：銀色隊（silver/white + cyan 光）與紅色隊（crimson/dark red + orange 光）
  ——**兩隊輪廓必須相同，只換配色**，玩家才能秒認棋種
- 棋子縮到 40×40 px 仍要能辨認 → 輪廓簡潔、對比強烈、細節少
- **方向性是命**：這個遊戲的棋子有朝向（鏡面方向、裝甲正面、雷射口），
  圖片必須讓玩家一眼看出朝向。每項的提示詞已寫明方向要求，**不要讓 AI 自由發揮方向**
- 畫面中**不可以有任何文字或字母**
- 光影：單一光源從正上方，避免斜影（俯視棋子斜影會誤導方向判讀）

**建議給 ChatGPT 的開場白**（每個 session 先貼一次）：

> You are generating a consistent set of top-down board game piece sprites for a
> sci-fi laser strategy game. All images: 1024x1024, transparent background PNG,
> strict top-down view (no perspective), clean bold silhouettes readable at small
> sizes, single overhead lighting, no text or letters anywhere, consistent
> futuristic robot-tech style across the whole set. Two team colorways will be
> requested per piece: SILVER team (brushed silver-white armor with cyan glowing
> accents) and RED team (dark crimson armor with orange glowing accents).
> Same silhouette for both teams, only colors change.

---

## 1. 棋子（5 種 × 2 隊色 = 10 張）★ 最優先

### 1.1 指揮核心（King，即法老）— `silver_king.png` / `red_king.png`

被雷射打中就輸，全遊戲最重要的棋子。外觀要「一看就是最重要的」。

> A majestic robotic command core unit, top-down view: a tall central crystalline
> energy core surrounded by a ring of protective armor petals, clearly the most
> important "king" piece of the set. Radially symmetric (no facing direction
> needed). SILVER team colorway: brushed silver-white armor, bright cyan glowing
> core. 1024x1024, transparent background, top-down, no text.

（紅隊版：把最後一句換成 RED team colorway: dark crimson armor, orange glowing core.）

### 1.2 雷射砲台（Emitter，即 Sphinx）— `silver_emitter.png` / `red_emitter.png`

固定在角落、每回合發射雷射的砲台。**砲口方向必須極明顯**（圖片預設朝上，
遊戲內用程式旋轉）。

> A heavy stationary laser cannon turret, top-down view: a wide armored circular
> base with one single oversized laser barrel pointing STRAIGHT UP in the image
> (12 o'clock direction), barrel clearly longer than the base radius so the facing
> direction is unmistakable, glowing charged laser tip. SILVER team colorway:
> brushed silver-white armor, cyan glowing barrel tip. 1024x1024, transparent
> background, top-down, no text.

### 1.3 單面鏡衛兵（Mirror，即 Pyramid）— `silver_mirror.png` / `red_mirror.png`

最多的棋子（每隊 7 顆）。**一個直角三角形機體，斜邊是鏡面**：斜邊反射雷射、
另外兩邊是弱點。方向規格（極重要）：

> A right-triangle shaped robotic deflector drone, STRICT top-down view: the piece
> occupies the LOWER-LEFT half of a square footprint — its two straight armored
> edges face LEFT and DOWN, and its diagonal edge (hypotenuse) runs from top-left
> to bottom-right, made of a brilliant reflective mirror surface glowing like
> polished chrome with energy shimmer. The mirror hypotenuse must visually contrast
> with the two dark armored edges. SILVER team colorway: silver-white armor edges,
> cyan energy shimmer on the mirror. 1024x1024, transparent background, top-down,
> no text.

（⚠️ 收圖時檢查：鏡面必須在「左上→右下」對角線上、實體在左下半。方向錯了整組重生。）

### 1.4 雙面鏡飛梭（Twin Mirror，即 Scarab）— `silver_twinmirror.png` / `red_twinmirror.png`

兩面都是鏡子、不可能被摧毀、還能跟其他棋子換位的滑翔機體。外觀＝一條斜放的雙面鏡。

> A sleek twin-sided mirror glider unit, STRICT top-down view: a thin elongated
> double-sided mirror blade placed diagonally from top-left to bottom-right of the
> square footprint, BOTH long faces are brilliant reflective chrome mirror surfaces,
> small robotic thruster pods at the two ends of the blade. It should look agile
> and indestructible, clearly different from a triangle piece — this one is a thin
> diagonal blade, not a filled triangle. SILVER team colorway with cyan shimmer.
> 1024x1024, transparent background, top-down, no text.

### 1.5 裝甲護衛（Shield，即 Anubis）— `silver_shield.png` / `red_shield.png`

正面免疫雷射、側背面脆弱的重裝衛兵。**正面盾牌方向必須極明顯**（圖片預設朝上）。

> A heavy robotic shield guardian, STRICT top-down view: a stocky armored unit
> carrying one massive glowing tower shield on its TOP side (12 o'clock direction
> of the image), the shield clearly wider than the body and visibly thick, while
> its other three sides show exposed mechanical parts (the weak sides). Facing
> direction must be unmistakable from the shield position. SILVER team colorway:
> silver-white armor, cyan glowing shield face. 1024x1024, transparent background,
> top-down, no text.

---

## 2. 棋盤與格子（4 張）

### 2.1 棋盤底圖 — `board_bg.png`
> A dark futuristic game board background texture, subtle hexagonal-free clean
> metal deck plating with faint grid seams, very dark navy-charcoal tones so game
> pieces pop on top, no glow spots in the middle, uniform edge-to-edge, 2048x1638
> (10:8 aspect ratio), no text.

### 2.2 一般格 — `tile_normal.png`（可選，若用程式畫格線則不需要）
> A single square floor tile of dark brushed metal with a very subtle inner bevel,
> flat top-down, uniform, tileable, 512x512, no text.

### 2.3 銀隊限制格 — `tile_silver_only.png`
> A single square floor tile of dark metal with a subtle glowing CYAN border inset
> and a faint cyan emblem in the center (abstract geometric mark, not a letter),
> flat top-down, tileable, 512x512, no text.

### 2.4 紅隊限制格 — `tile_red_only.png`
（同上，CYAN→ORANGE-RED、cyan→orange）

---

## 3. 雷射特效（5 張）★ 遊戲的靈魂

光束建議遊戲內用程式畫線（顏色/發光用 shader 或半透明疊加），
但以下貼圖能大幅提升質感：

### 3.1 光束段 — `laser_beam.png`
> A horizontal laser beam segment: intense bright red-orange core with a soft outer
> glow, perfectly straight, seamlessly tileable horizontally, on transparent
> background, 512x128, no text.

### 3.2 光束轉折點 — `laser_corner.png`
> A 90-degree laser beam corner joint: an intense bright red-orange laser bending
> from entering LEFT side to exiting TOP side with a small bright flare at the bend,
> transparent background, 256x256, no text.

### 3.3 命中爆閃 — `laser_hit.png`
> A radial laser impact burst: bright white-orange explosion flash with sparks and
> a shockwave ring, centered, transparent background, 512x512, no text.

### 3.4 鏡面反射閃光 — `laser_reflect.png`
> A small sharp star-shaped glint of light, bright white with cyan tint, centered,
> transparent background, 256x256, no text.

### 3.5 發射口充能 — `laser_muzzle.png`
> A charging laser muzzle flash: concentrated glowing energy orb with radial light
> streaks, red-orange, centered, transparent background, 256x256, no text.

---

## 4. UI 圖示（6 張）

統一規格：512×512、透明背景、單色系線條風（淺灰白 #E8E8F0 線條 + 微發光）、
無文字。提示詞模板：

> A minimal glowing line-art game UI icon of {主題}, light gray-white strokes with
> a subtle cyan glow, centered, transparent background, 512x512, flat, no text.

| 檔名 | {主題} 填入 |
|---|---|
| `icon_rotate_cw.png` | a clockwise circular rotation arrow |
| `icon_rotate_ccw.png` | a counter-clockwise circular rotation arrow |
| `icon_undo.png` | an undo curved arrow pointing left |
| `icon_ai.png` | a robot head with circuit patterns |
| `icon_puzzle.png` | a target crosshair with a laser dot |
| `icon_swap.png` | two opposing curved arrows forming a swap cycle |

（音樂/音效圖示沿用前作 `music_icon.png` / `sound_icon.png`。）

---

## 5. 應用程式圖示（1 張）

### `app_icon.png`
> A square game app icon: a dramatic close-up of a silver robotic deflector piece
> reflecting a bright red laser beam at a 90-degree angle against a dark navy
> background, bold, high contrast, readable at small sizes, subtle vignette,
> 1024x1024, NO text, no border.

---

## 6. 收圖檢查清單（每張圖生成後核對）

- [ ] 透明背景（棋子/特效/圖示類）？貼到深色底上檢查邊緣沒有白邊
- [ ] 正俯視、無透視、無斜長影？
- [ ] **方向正確**：砲台朝上？三角鏡的鏡面在左上→右下、實體在左下半？護衛盾牌朝上？
- [ ] 兩隊同棋種輪廓一致、只差配色？
- [ ] 縮到 40px 後仍可辨認棋種與朝向？
- [ ] 整組風格一致（同一種金屬質感、同一種發光語彙）？
- [ ] 圖中沒有任何文字、字母、浮水印？

## 7. 檔名總表

```
assets/
  silver_king.png      red_king.png
  silver_emitter.png   red_emitter.png
  silver_mirror.png    red_mirror.png        ← 每隊 7 顆共用同一張
  silver_twinmirror.png red_twinmirror.png
  silver_shield.png    red_shield.png
  board_bg.png  tile_normal.png  tile_silver_only.png  tile_red_only.png
  laser_beam.png  laser_corner.png  laser_hit.png  laser_reflect.png  laser_muzzle.png
  icon_rotate_cw.png  icon_rotate_ccw.png  icon_undo.png  icon_ai.png  icon_puzzle.png  icon_swap.png
  app_icon.png
```

合計：**26 張**（棋子 10、棋盤 4、雷射 5、UI 6、app icon 1）。
優先順序：棋子 10 張 → 雷射 5 張 → 其餘。
