"""產生 data/laser_table.json —— 雷射互動真值表（全專案唯一權威來源）。

LASER_TABLE[type][orientation][beam_dir] 表示：
    一道「行進方向為 beam_dir」的光束，打到「朝向為 orientation 的 type 棋子」時的結果。
    結果為 {"result": "reflect", "dir": 新方向} | {"result": "absorb"} | {"result": "hit"}

方向與朝向定義（見 docs/agent_manual/01_conventions.md）：
    0=N（row-1）、1=E（col+1）、2=S（row+1）、3=W（col-1）
    PYRAMID orientation k：鏡面朝向 {k, k+1}，其餘兩面為弱點。
    SCARAB orientation 0 = '\\'（NW-SE 對角線）、1 = '/'；2、3 與 0、1 等價。
    ANUBIS orientation k：盾牌面朝 k 方向，正面吸收、其餘面弱點。
    SPHINX：任何面皆免疫（吸收）。PHARAOH：任何面皆弱點。

執行方式（在專案根目錄）：
    .\\venv\\Scripts\\python.exe scripts\\gen_laser_table.py
內建自我檢查全部通過才會寫檔。手動修改 laser_table.json 是被禁止的；要改就改這裡再重生。
"""
import json
import os

N, E, S, W = 0, 1, 2, 3
DIRS = (N, E, S, W)
PIECE_TYPES = ("PHARAOH", "SPHINX", "SCARAB", "ANUBIS", "PYRAMID")

REFLECT_BACKSLASH = {N: W, E: S, S: E, W: N}   # '\' 鏡面：交換座標分量
REFLECT_SLASH = {N: E, E: N, S: W, W: S}        # '/' 鏡面：交換並取負


def opposite(d: int) -> int:
    return (d + 2) % 4


def entry(piece_type: str, orientation: int, beam_dir: int) -> dict:
    """回傳單一格的互動結果。face = 光束打到的棋子面（= 光束來向的反方向）。"""
    face = opposite(beam_dir)

    if piece_type == "PHARAOH":
        return {"result": "hit"}

    if piece_type == "SPHINX":
        return {"result": "absorb"}

    if piece_type == "ANUBIS":
        if face == orientation:                 # 正面（盾牌面）被打中
            return {"result": "absorb"}
        return {"result": "hit"}

    if piece_type == "SCARAB":
        mapping = REFLECT_BACKSLASH if orientation % 2 == 0 else REFLECT_SLASH
        return {"result": "reflect", "dir": mapping[beam_dir]}

    if piece_type == "PYRAMID":
        face_a = orientation % 4                # 鏡面朝向的兩個方位
        face_b = (orientation + 1) % 4
        if face == face_a:
            return {"result": "reflect", "dir": face_b}
        if face == face_b:
            return {"result": "reflect", "dir": face_a}
        return {"result": "hit"}

    raise ValueError(f"unknown piece type: {piece_type}")


def build_table() -> dict:
    return {
        pt: [[entry(pt, o, d) for d in DIRS] for o in range(4)]
        for pt in PIECE_TYPES
    }


def self_check(table: dict) -> None:
    for pt in PIECE_TYPES:
        for o in range(4):
            results = [table[pt][o][d]["result"] for d in DIRS]
            counts = {r: results.count(r) for r in set(results)}
            if pt == "PHARAOH":
                assert counts == {"hit": 4}, (pt, o, counts)
            elif pt == "SPHINX":
                assert counts == {"absorb": 4}, (pt, o, counts)
            elif pt == "ANUBIS":
                assert counts == {"absorb": 1, "hit": 3}, (pt, o, counts)
            elif pt == "SCARAB":
                assert counts == {"reflect": 4}, (pt, o, counts)
            elif pt == "PYRAMID":
                assert counts == {"reflect": 2, "hit": 2}, (pt, o, counts)

            # 反射可逆性：d 反射成 d' ⇒ 反向光 opposite(d') 必反射成 opposite(d)
            for d in DIRS:
                e = table[pt][o][d]
                if e["result"] == "reflect":
                    back = table[pt][o][opposite(e["dir"])]
                    assert back["result"] == "reflect", (pt, o, d)
                    assert back["dir"] == opposite(d), (pt, o, d)

    # PYRAMID 的鏡面幾何必須與 SCARAB 的對角線一致：
    # orientation 0/2 的鏡面是 '\'，1/3 是 '/'
    for o in range(4):
        mapping = REFLECT_BACKSLASH if o % 2 == 0 else REFLECT_SLASH
        for d in DIRS:
            e = table["PYRAMID"][o][d]
            if e["result"] == "reflect":
                assert e["dir"] == mapping[d], ("PYRAMID mirror geometry", o, d)

    # 抽查（黃金向量，來自已驗證的 classic 開局光束路徑）：
    assert table["PYRAMID"][0][S] == {"result": "reflect", "dir": E}
    assert table["PYRAMID"][0][W] == {"result": "reflect", "dir": N}
    assert table["PYRAMID"][0][N] == {"result": "hit"}
    assert table["PYRAMID"][2][N] == {"result": "reflect", "dir": W}
    assert table["PYRAMID"][3][E] == {"result": "reflect", "dir": N}
    assert table["SCARAB"][0][E] == {"result": "reflect", "dir": S}
    assert table["SCARAB"][1][S] == {"result": "reflect", "dir": W}
    assert table["ANUBIS"][2][N] == {"result": "absorb"}   # 盾朝 S、光束向 N＝正面
    assert table["ANUBIS"][2][S] == {"result": "hit"}


def main() -> None:
    table = build_table()
    self_check(table)
    out = {
        "_readme": [
            "雷射互動真值表。由 scripts/gen_laser_table.py 產生，禁止手動修改。",
            "用法：LASER_TABLE[type][orientation][beam_dir] -> reflect/absorb/hit。",
            "beam_dir 是光束行進方向：0=N 1=E 2=S 3=W。",
            "Python 引擎與未來 JS 手機版必須載入同一份檔案，保證雙平台規則一致。",
        ],
        "directions": {"N": 0, "E": 1, "S": 2, "W": 3},
        "table": table,
    }
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "data", "laser_table.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK: self-check passed, wrote {path}")


if __name__ == "__main__":
    main()
