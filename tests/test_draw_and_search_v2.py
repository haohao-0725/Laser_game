"""桌面 AI v2：三次同形必須是搜尋與 GUI 都認得的真正終局。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gui.game_controller import GameController
from khet.ai import _Searcher, search
from khet.engine import Rotate, apply_action, initial_state, legal_actions, winner


def _repeat_classic_opening(controller: GameController) -> None:
    """用兩顆盾衛的可逆旋轉，讓 Classic 初始局面出現第三次。"""
    cycle = (
        Rotate(3, 7, True),
        Rotate(4, 0, True),
        Rotate(3, 7, False),
        Rotate(4, 0, False),
    )
    for _ in range(2):
        for action in cycle:
            controller.do_action(action)


def test_search_scores_third_repetition_as_draw():
    state = initial_state("classic")
    action = next(
        a for a in legal_actions(state)
        if apply_action(state, a)[1].event != "hit"
    )
    child, _ = apply_action(state, action)

    _, info = search(
        state,
        max_depth=1,
        time_limit=1.0,
        history_counts={state: 1, child: 2},
    )

    assert info["root_scores"][action] == 0


def test_search_rejects_already_drawn_position():
    state = initial_state("classic")
    with pytest.raises(RuntimeError, match="三次同形"):
        search(state, max_depth=1, history_counts={state: 3})


def test_controller_detects_repetition_and_board_rejects_extra_move():
    from PyQt6.QtWidgets import QApplication
    from gui.board_widget import BoardWidget

    app = QApplication.instance() or QApplication([])
    controller = GameController("classic")
    initial = controller.state
    _repeat_classic_opening(controller)

    assert controller.state == initial
    assert controller.is_draw_by_repetition()

    board = BoardWidget(controller)
    before = controller.state
    board.play_action(legal_actions(before)[0])
    app.processEvents()
    assert controller.state == before


def test_search_reports_v2_diagnostics():
    _, info = search(initial_state("dynasty"), max_depth=1, time_limit=1.0)
    assert info["depth"] == 1
    assert info["qnodes"] > 0
    assert {"nodes", "tt_hits", "cutoffs", "root_scores"} <= info.keys()


def test_quiescence_sees_mate_threat_beyond_nominal_depth():
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "SILVER", 4, 0, 0),
        ("PHARAOH", "RED", 5, 6, 0),
        ("PYRAMID", "SILVER", 4, 4, 0),
        ("ANUBIS", "SILVER", 3, 6, 0),
    ]))
    state = ("SILVER", pieces)
    action, _ = search(state, max_depth=1, time_limit=3.0)
    defended, _ = apply_action(state, action)

    assert all(
        winner(apply_action(defended, reply)[0]) != "RED"
        for reply in legal_actions(defended)
    )


def test_quiescence_includes_actions_that_evade_self_hit():
    pieces = tuple(sorted([
        ("SPHINX", "RED", 0, 0, 2),
        ("SPHINX", "SILVER", 9, 7, 0),
        ("PHARAOH", "RED", 5, 1, 0),
        ("PHARAOH", "SILVER", 4, 6, 0),
        ("PYRAMID", "SILVER", 9, 5, 0),
    ]))
    state = ("SILVER", pieces)
    entries = _Searcher(time.monotonic() + 1.0).forcing_entries(state)

    assert any(
        laser.event != "hit" or laser.hit_piece[1] != "SILVER"
        for _, _, laser in entries
    )
