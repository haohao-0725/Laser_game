"""發布前煙霧測試。全部通過才准 Release。
執行：.\\venv\\Scripts\\python.exe scripts\\smoke_test.py
"""
import os
import random
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def step(name):
    print(f"[..] {name}", flush=True)


def ok(name):
    print(f"[OK] {name}", flush=True)


def test_engine_regression():
    step("引擎回歸（pytest）")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-1000:])
        raise SystemExit("pytest 失敗")
    ok("引擎回歸")


def test_gui_build():
    step("GUI 建構 + 走子 + 存讀檔")
    from PyQt6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    from gui.game_controller import GameController
    from khet.engine import legal_actions

    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    app.processEvents()
    rng = random.Random(1)
    for _ in range(3):
        win.controller.do_action(rng.choice(legal_actions(win.controller.state)))
    save = os.path.join(ROOT, "_smoke_save.json")
    win.controller.save(save)
    GameController.load(save)
    os.remove(save)
    win.close()
    ok("GUI 建構")


def test_ai_selfplay():
    step("AI 快速自對戰")
    from khet.ai import choose_action
    from khet.engine import initial_state, apply_action, winner
    state = initial_state("classic")
    for _ in range(6):
        if winner(state) is not None:
            break
        a = choose_action(state, "easy", time_limit=1.0)
        state, _ = apply_action(state, a)
    ok("AI 自對戰")


def test_puzzle_catalog():
    step("謎題目錄載入 + 抽題檢查")
    from gui.puzzles_data import load_catalog, daily_puzzle
    cat = load_catalog()
    assert len(cat) >= 17, f"謎題數不足：{len(cat)}"
    assert daily_puzzle(cat) is not None
    ok(f"謎題目錄（{len(cat)} 題）")


def main():
    test_engine_regression()
    test_gui_build()
    test_ai_selfplay()
    test_puzzle_catalog()
    print("\n全部 smoke test 通過 ✅")


if __name__ == "__main__":
    main()
