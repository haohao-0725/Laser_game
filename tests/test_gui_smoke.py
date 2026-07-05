"""GUI 煙霧測試（offscreen）：視窗可建構、走子、悔棋、存讀檔不炸。"""
import os
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from khet.engine import legal_actions


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_main_window_and_gameplay(app, tmp_path):
    from gui.main_window import MainWindow

    win = MainWindow()
    win.show()
    app.processEvents()

    # 直接透過 controller 走 5 手（跳過動畫），棋盤重繪不應例外
    rng = random.Random(7)
    for _ in range(5):
        acts = legal_actions(win.controller.state)
        win.controller.do_action(rng.choice(acts))
        win.board.update()
        app.processEvents()

    # 悔棋
    assert win.controller.ply_count == 5
    win.undo()
    assert win.controller.ply_count == 4

    # 存讀檔 roundtrip
    path = str(tmp_path / "save.json")
    win.controller.save(path)
    from gui.game_controller import GameController
    loaded = GameController.load(path)
    assert loaded.state == win.controller.state
    assert loaded.ply_count == 4

    # 換佈局新局
    win.new_game("dynasty")
    assert win.controller.layout == "dynasty"
    app.processEvents()
    win.close()


def test_board_renders_to_image(app):
    """棋盤實際渲染一張圖（驗證 paintEvent 整條路徑，含素材載入）。"""
    from gui.board_widget import BoardWidget
    from gui.game_controller import GameController

    board = BoardWidget(GameController("classic"))
    board.resize(1000, 800)
    board.show()
    app.processEvents()
    pixmap = board.grab()
    assert not pixmap.isNull() and pixmap.width() > 0


def test_ai_mode_wiring(app):
    """人機模式：背景任務同步執行 → 結果經 signal 進 board（不跑動畫計時器）。"""
    from gui.main_window import MainWindow, _Worker
    from khet.engine import legal_actions

    win = MainWindow()
    win.set_ai_mode("easy")
    assert win.ai_difficulty == "easy" and win.controller.ply_count == 0

    # 玩家（銀方）走一手 → 輪到 AI（紅方）
    win.controller.do_action(legal_actions(win.controller.state)[0])
    assert win.controller.state[0] == "RED"

    # 同步跑背景任務（不經 thread pool），驗證 token 防護與落子路徑
    win._token += 1
    win.board.input_locked = True
    task = _Worker(win._compute_ai_move, win._token, win._signals)
    task.run()
    app.processEvents()
    assert win.controller.ply_count == 2          # AI 已落子
    assert win.board.input_locked is False

    # 過期 token 的結果要被丟棄
    stale = _Worker(win._compute_ai_move, win._token - 1, win._signals)
    stale.run()
    app.processEvents()
    assert win.controller.ply_count == 2
    win.close()


def test_puzzle_mode_solves(app, tmp_path, monkeypatch):
    """謎題模式：載入一題 1 手謎題，用其記錄的解答首著走一手 → 破解成功。"""
    import gui.user_data as ud
    monkeypatch.setattr(ud, "_PATH", str(tmp_path / "user_data.json"))
    monkeypatch.setattr(ud, "_APPDIR", str(tmp_path))

    from gui.main_window import MainWindow
    from gui.puzzles_data import load_catalog
    from khet.engine import action_from_dict, winner

    catalog = load_catalog()
    n1 = [p for p in catalog if p["difficulty"] == 1]
    if not n1:
        pytest.skip("目錄無 1 手謎題")
    puzzle = n1[0]

    win = MainWindow()
    win.start_puzzle(puzzle)
    assert win.puzzle is not None
    action = action_from_dict(puzzle["solution_first_move"])
    win.controller.do_action(action)
    win.board.update()
    app.processEvents()
    assert winner(win.controller.state) == puzzle["player"]
    win.close()


def test_settings_and_stats_persist(app, tmp_path, monkeypatch):
    import gui.user_data as ud
    monkeypatch.setattr(ud, "_PATH", str(tmp_path / "user_data.json"))
    monkeypatch.setattr(ud, "_APPDIR", str(tmp_path))

    data = ud.load()
    ud.record_win(data, "ai_medium")
    ud.mark_puzzle_solved(data, "n1_001")
    reloaded = ud.load()
    assert reloaded["wins"]["ai_medium"] == 1
    assert "n1_001" in reloaded["puzzles_solved"]


def test_engine_layer_has_no_qt_import():
    """鐵律：khet/ 不得依賴 Qt。"""
    import khet.engine as eng
    src = open(eng.__file__, encoding="utf-8").read()
    assert "PyQt" not in src


def test_puzzles_layer_has_no_qt_import():
    import khet.puzzles as pz
    src = open(pz.__file__, encoding="utf-8").read()
    assert "PyQt" not in src
