"""雷射真值表測試：5 種棋 × 4 朝向 × 4 入射方向 = 80 格全部斷言。
真值表若錯，引擎/AI/謎題全部下游都會被污染——這是全專案最重要的測試。
CASES 的期望值是獨立重寫的展開式；若有人手改 JSON 或改壞生成器，這裡會抓到。"""
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data", "laser_table.json"), encoding="utf-8") as f:
    TABLE = json.load(f)["table"]

N, E, S, W = 0, 1, 2, 3


def r(d):
    return {"result": "reflect", "dir": d}


HIT = {"result": "hit"}
ABSORB = {"result": "absorb"}

# '\' 鏡面（PYRAMID ori 0/2 的幾何、SCARAB ori 0）：N→W E→S S→E W→N
# '/' 鏡面（PYRAMID ori 1/3、SCARAB ori 1）：N→E E→N S→W W→S
CASES = []
for o in range(4):
    for d in range(4):
        CASES.append(("PHARAOH", o, d, HIT))
        CASES.append(("SPHINX", o, d, ABSORB))
        # ANUBIS：盾面朝 o，光束行進方向 d 打到的面是 (d+2)%4
        CASES.append(("ANUBIS", o, d, ABSORB if (d + 2) % 4 == o else HIT))
        # SCARAB：永遠反射
        mapping = [W, S, E, N] if o % 2 == 0 else [E, N, W, S]
        CASES.append(("SCARAB", o, d, r(mapping[d])))
        # PYRAMID：鏡面朝 {o, o+1}
        face = (d + 2) % 4
        if face == o:
            CASES.append(("PYRAMID", o, d, r((o + 1) % 4)))
        elif face == (o + 1) % 4:
            CASES.append(("PYRAMID", o, d, r(o)))
        else:
            CASES.append(("PYRAMID", o, d, HIT))


@pytest.mark.parametrize("ptype,ori,beam,expected", CASES)
def test_laser_table_cell(ptype, ori, beam, expected):
    assert TABLE[ptype][ori][beam] == expected
