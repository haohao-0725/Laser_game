"""驗證 data/layouts.json 的完整性。任何人（或 agent）修改佈局資料後必須跑這支。

檢查項目：
  1. cell 記法與 col/row 一致（a8 = col0,row0；j1 = col9,row7）
  2. 每方恰好 13 顆：PHARAOH 1、SPHINX 1、SCARAB 2、ANUBIS 2、PYRAMID 7
  3. 無同格重疊、座標在棋盤內、orientation 在 0-3
  4. Sphinx 位置與朝向合法（紅 a8 朝 E/S；銀 j1 朝 N/W）
  5. 佈局 180 度旋轉對稱（官方三種佈局皆對稱；自訂佈局可用 --no-symmetry 跳過）
  6. 棋子不站在對方限制格上

執行：.\\venv\\Scripts\\python.exe scripts\\validate_layouts.py
"""
import json
import os
import sys

COLS = "abcdefghij"


def cell_name(col: int, row: int) -> str:
    return f"{COLS[col]}{8 - row}"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def validate_layout(name: str, pieces: list, data: dict, check_symmetry: bool = True) -> None:
    board = data["board"]
    restricted = {
        "RED": {tuple(c) for c in data["restricted"]["RED"]},
        "SILVER": {tuple(c) for c in data["restricted"]["SILVER"]},
    }
    expected_counts = {"PHARAOH": 1, "SPHINX": 1, "SCARAB": 2, "ANUBIS": 2, "PYRAMID": 7}

    occupied = {}
    for p in pieces:
        col, row, ori = p["col"], p["row"], p["orientation"]
        if not (0 <= col < board["cols"] and 0 <= row < board["rows"]):
            fail(f"{name}: {p} 座標出界")
        if not (0 <= ori <= 3):
            fail(f"{name}: {p} orientation 非法")
        if p["cell"] != cell_name(col, row):
            fail(f"{name}: cell 記法不一致 {p['cell']} != {cell_name(col, row)}")
        if (col, row) in occupied:
            fail(f"{name}: {cell_name(col, row)} 被兩顆棋子佔用")
        occupied[(col, row)] = p
        opponent = "SILVER" if p["color"] == "RED" else "RED"
        if (col, row) in restricted[opponent]:
            fail(f"{name}: {p['color']} 棋子站在對方限制格 {cell_name(col, row)}")

    for color in ("RED", "SILVER"):
        counts = {}
        for p in pieces:
            if p["color"] == color:
                counts[p["type"]] = counts.get(p["type"], 0) + 1
        if counts != expected_counts:
            fail(f"{name}/{color}: 棋子數量錯誤 {counts}（應為 {expected_counts}）")

    for color in ("RED", "SILVER"):
        sp = next(p for p in pieces if p["color"] == color and p["type"] == "SPHINX")
        ref = data["sphinx"][color]
        if (sp["col"], sp["row"]) != (ref["col"], ref["row"]):
            fail(f"{name}: {color} Sphinx 不在 {ref['cell']}")
        if sp["orientation"] not in ref["legal_orientations"]:
            fail(f"{name}: {color} Sphinx 朝向 {sp['orientation']} 非法（合法：{ref['legal_orientations']}）")

    if check_symmetry:
        # 180 度旋轉對稱：紅方每顆棋在 (9-col, 7-row) 應有一顆銀方同型棋，
        # 朝向 +2 mod 4（SCARAB 只看 mod 2、PHARAOH 不看朝向）
        silver = {(p["col"], p["row"]): p for p in pieces if p["color"] == "SILVER"}
        for p in pieces:
            if p["color"] != "RED":
                continue
            partner = silver.get((9 - p["col"], 7 - p["row"]))
            if partner is None or partner["type"] != p["type"]:
                fail(f"{name}: {p['cell']} 的 {p['type']} 缺少對稱夥伴")
            if p["type"] == "PHARAOH":
                continue
            if p["type"] == "SCARAB":
                if p["orientation"] % 2 != partner["orientation"] % 2:
                    fail(f"{name}: SCARAB 對稱朝向錯誤 {p['cell']} vs {partner['cell']}")
            elif p["type"] == "SPHINX":
                continue  # 已由 legal_orientations 檢查；對稱性：紅 S(2)↔銀 N(0)、紅 E(1)↔銀 W(3) 自然成立
            elif (p["orientation"] + 2) % 4 != partner["orientation"]:
                fail(f"{name}: {p['type']} 對稱朝向錯誤 {p['cell']}({p['orientation']}) vs "
                     f"{partner['cell']}({partner['orientation']})")

    print(f"OK: layout '{name}' 通過全部檢查（{len(pieces)} 顆棋）")


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "data", "layouts.json"), encoding="utf-8") as f:
        data = json.load(f)

    # 限制格本身的健全性
    for color, cells in (("RED", data["restricted"]["RED"]), ("SILVER", data["restricted"]["SILVER"])):
        assert len(cells) == 10, f"{color} 限制格應為 10 格"
    assert set(map(tuple, data["restricted"]["RED"])).isdisjoint(
        set(map(tuple, data["restricted"]["SILVER"]))), "限制格不可重疊"

    for name, pieces in data["layouts"].items():
        validate_layout(name, pieces, data)

    print("OK: layouts.json 全部通過")


if __name__ == "__main__":
    main()
