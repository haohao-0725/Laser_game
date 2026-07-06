"""Phase 6 規則一致性測試（pytest 包一層，方便 CI 一起跑）：
Python 生成向量 → Node 跑 engine.js 逐一比對 → 必須 N/N PASS。
需要 node 在 PATH；沒有就跳過。"""
import os
import shutil
import subprocess

import pytest

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
