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


def test_engine_layer_has_no_qt_import():
    """鐵律：khet/ 不得依賴 Qt。"""
    import khet.engine as eng
    src = open(eng.__file__, encoding="utf-8").read()
    assert "PyQt" not in src
