"""Phase 6 規則一致性測試（pytest 包一層，方便 CI 一起跑）：
Python 生成向量 → Node 跑 engine.js 逐一比對 → 必須 N/N PASS。
需要 node 在 PATH；沒有就跳過。"""
import os
import json
import random
import shutil
import subprocess

import pytest

from khet.ai import evaluate
from khet.engine import apply_action, initial_state, legal_actions, winner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在 PATH")
def test_web_rule_consistency():
    py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    py = py if os.path.exists(py) else "python"
    # subprocess 輸出含 UTF-8 中文，Windows 預設 cp950 會解碼失敗 → 明確指定
    kw = dict(cwd=ROOT, capture_output=True, text=True,
              encoding="utf-8", errors="replace")
    # 重新匯出資料與向量，確保比對的是當前規則
    subprocess.run([py, "scripts/export_web_data.py"], check=True, **kw)
    subprocess.run([py, "scripts/gen_test_vectors.py", "--count", "400"],
                   check=True, **kw)
    r = subprocess.run(["node", "www/js/vectors_test.js"], **kw)
    assert r.returncode == 0, f"JS 引擎與 Python 規則不一致：\n{r.stdout}\n{r.stderr}"
    assert "PASS" in r.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在 PATH")
def test_web_ai_v2_consistency(tmp_path):
    kw = dict(cwd=ROOT, capture_output=True, text=True,
              encoding="utf-8", errors="replace")
    self_test = subprocess.run(["node", "www/js/ai_test.js"], **kw)
    assert self_test.returncode == 0, f"JS AI v2 自測失敗：\n{self_test.stdout}\n{self_test.stderr}"
    assert "PASS" in self_test.stdout

    rng = random.Random(20260716)
    states = []
    for layout in ("classic", "imhotep", "dynasty"):
        state = initial_state(layout)
        for _ in range(8):
            states.append(state)
            if winner(state) is not None:
                break
            state, _ = apply_action(state, rng.choice(legal_actions(state)))

    payload = [
        {"player": state[0], "pieces": [list(piece) for piece in state[1]]}
        for state in states
    ]
    path = tmp_path / "ai_states.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(["node", "www/js/ai_test.js", str(path)], **kw)
    assert result.returncode == 0, f"JS AI 評估失敗：\n{result.stdout}\n{result.stderr}"
    assert json.loads(result.stdout) == [evaluate(state) for state in states]
