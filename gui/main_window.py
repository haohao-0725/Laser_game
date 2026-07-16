"""主視窗：選單、狀態列、勝負/和局、人機對戰、謎題模式、設定與戰績。"""
import os

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QFileDialog, QLabel, QMainWindow, QMessageBox,
)

from gui import assets, user_data
from gui.assets import ASSETS_DIR, play_sound
from gui.board_widget import BoardWidget
from gui.game_controller import GameController
from gui.puzzle_dialog import PuzzleDialog
from gui.puzzles_data import DIFFICULTY_NAMES

LAYOUT_NAMES = {"classic": "經典（Classic）",
                "imhotep": "印和闐（Imhotep）",
                "dynasty": "王朝（Dynasty）"}
COLOR_NAMES = {"SILVER": "銀方", "RED": "紅方"}
AI_NAMES = {"easy": "簡單", "medium": "中等", "hard": "困難"}
AI_COLOR = "RED"            # 人機模式 AI 執紅（後手），玩家執銀先手

RULES_TEXT = """\
【目標】用雷射擊落對方的指揮核心（王）。

【回合】每回合必選一個行動：
　1. 移動自己一顆棋到相鄰空格（8 方向）
　2. 原地旋轉 90°（雷射砲台只能在兩個合法朝向間切換、不可移動）
　行動結束後，你的雷射砲台「強制」發射！

【雷射】光束被鏡面反射、被盾牌正面擋下；
　打中其他面的棋子會被移除——包括你自己的棋！

【特殊】雙面鏡（細長斜刀）永遠不會被擊落，
　且可以與相鄰的單面鏡/盾衛（不分敵我）交換位置。

【限制格】帶色框的格子只有該色棋子能進入。

【和局】同一局面第三次出現判和。銀方先手。"""


class _WorkerSignals(QObject):
    done = pyqtSignal(int, object)      # (token, action)


class _Worker(QRunnable):
    """背景計算一手棋（AI 出手或謎題防守方應手）。"""
    def __init__(self, fn, token: int, signals: _WorkerSignals):
        super().__init__()
        self.fn = fn
        self.token = token
        self.signals = signals

    def run(self) -> None:
        action = self.fn()
        self.signals.done.emit(self.token, action)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷射對決 Laser Duel")
        icon_path = os.path.join(ASSETS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.data = user_data.load()
        assets.sound_enabled = self.data["sound_enabled"]

        self.controller = GameController("classic")
        self.ai_difficulty: str | None = None      # None = 雙人
        self.puzzle: dict | None = None            # None = 非謎題模式
        self.puzzle_moves_used = 0
        self._win_recorded = False

        self._token = 0
        self._signals = _WorkerSignals()
        self._signals.done.connect(self._on_worker_done)

        self.board = BoardWidget(self.controller)
        self.board.turn_finished.connect(self._on_turn_finished)
        self.setCentralWidget(self.board)
        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label)
        self._build_menu()
        self._update_status()
        self.resize(1120, 820)

    # ------------------------------------------------------------ 選單
    def _build_menu(self) -> None:
        game_menu = self.menuBar().addMenu("遊戲(&G)")
        new_menu = game_menu.addMenu("新局")
        for key, name in LAYOUT_NAMES.items():
            act = QAction(name, self)
            act.triggered.connect(lambda _=False, k=key: self.new_game(k))
            new_menu.addAction(act)
        game_menu.addSeparator()
        undo_act = QAction("悔棋(&U)", self)
        undo_act.setShortcut("Ctrl+Z")
        undo_act.triggered.connect(self.undo)
        game_menu.addAction(undo_act)
        game_menu.addSeparator()
        save_act = QAction("存檔(&S)...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_game)
        game_menu.addAction(save_act)
        load_act = QAction("讀檔(&L)...", self)
        load_act.setShortcut("Ctrl+O")
        load_act.triggered.connect(self.load_game)
        game_menu.addAction(load_act)
        game_menu.addSeparator()
        quit_act = QAction("離開(&Q)", self)
        quit_act.triggered.connect(self.close)
        game_menu.addAction(quit_act)

        mode_menu = self.menuBar().addMenu("模式(&M)")
        pvp_act = QAction("雙人對戰（同機輪流）", self)
        pvp_act.triggered.connect(lambda: self.set_ai_mode(None))
        mode_menu.addAction(pvp_act)
        ai_menu = mode_menu.addMenu("人機對戰（你執銀方先手）")
        for key, name in AI_NAMES.items():
            act = QAction(f"AI 難度：{name}", self)
            act.triggered.connect(lambda _=False, k=key: self.set_ai_mode(k))
            ai_menu.addAction(act)
        mode_menu.addSeparator()
        puzzle_act = QAction("謎題模式(&P)...", self)
        puzzle_act.triggered.connect(self.open_puzzles)
        mode_menu.addAction(puzzle_act)
        hint_act = QAction("謎題提示(&H)", self)
        hint_act.triggered.connect(self.puzzle_hint)
        mode_menu.addAction(hint_act)

        opt_menu = self.menuBar().addMenu("選項(&O)")
        self.sound_act = QAction("音效", self, checkable=True)
        self.sound_act.setChecked(self.data["sound_enabled"])
        self.sound_act.toggled.connect(self.toggle_sound)
        opt_menu.addAction(self.sound_act)
        stats_act = QAction("戰績(&T)...", self)
        stats_act.triggered.connect(self.show_stats)
        opt_menu.addAction(stats_act)

        help_menu = self.menuBar().addMenu("說明(&H)")
        rules_act = QAction("遊戲規則(&R)", self)
        rules_act.triggered.connect(self.show_rules)
        help_menu.addAction(rules_act)

    # ------------------------------------------------------------ 模式與對局
    def set_ai_mode(self, difficulty: str | None) -> None:
        self.ai_difficulty = difficulty
        self.puzzle = None
        self.new_game(self.controller.layout)

    def new_game(self, layout: str) -> None:
        self._token += 1
        self.puzzle = None
        self.controller = GameController(layout)
        self._win_recorded = False
        self.board.set_controller(self.controller)
        self._update_status()

    def undo(self) -> None:
        if self.board.mode == "animating" or self.board.input_locked or self.puzzle:
            return
        self.controller.undo(2 if self.ai_difficulty else 1)
        self._reset_board_input()
        self._update_status()

    def _reset_board_input(self) -> None:
        self.board.selected = None
        self.board.overlay = []
        self.board.mode = "idle"
        self.board.input_locked = False
        self.board.update()

    def save_game(self) -> None:
        if self.puzzle:
            QMessageBox.information(self, "存檔", "謎題模式不支援存檔。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "存檔", "khet_save.json", "Khet 存檔 (*.json)")
        if path:
            self.controller.save(path)
            self.statusBar().showMessage(f"已存檔：{path}", 4000)

    def load_game(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "讀檔", "", "Khet 存檔 (*.json)")
        if not path:
            return
        try:
            controller = GameController.load(path)
        except Exception as exc:
            QMessageBox.warning(self, "讀檔失敗", f"無法載入存檔：\n{exc}")
            return
        self._token += 1
        self.puzzle = None
        self.controller = controller
        self._win_recorded = False
        self.board.set_controller(self.controller)
        self._update_status()
        self._maybe_start_ai()

    def show_rules(self) -> None:
        QMessageBox.information(self, "遊戲規則", RULES_TEXT)

    # ------------------------------------------------------------ 選項
    def toggle_sound(self, checked: bool) -> None:
        assets.sound_enabled = checked
        self.data["sound_enabled"] = checked
        user_data.save(self.data)

    def show_stats(self) -> None:
        w = self.data["wins"]
        text = (f"雙人對戰　銀方勝：{w['hotseat_SILVER']}　紅方勝：{w['hotseat_RED']}\n\n"
                f"人機對戰　你贏 AI（簡單）：{w['ai_easy']}　"
                f"（中等）：{w['ai_medium']}　（困難）：{w['ai_hard']}\n"
                f"　　　　　輸給 AI：{w['ai_lost']}\n\n"
                f"謎題通關：{len(self.data['puzzles_solved'])} 題")
        QMessageBox.information(self, "戰績", text)

    # ------------------------------------------------------------ 謎題模式
    def open_puzzles(self) -> None:
        dlg = PuzzleDialog(set(self.data["puzzles_solved"]), self)
        dlg.puzzle_chosen.connect(self.start_puzzle)
        dlg.exec()

    def start_puzzle(self, puzzle: dict) -> None:
        self._token += 1
        self.puzzle = puzzle
        self.puzzle_moves_used = 0
        self.ai_difficulty = None
        self.controller = GameController.from_state(puzzle["state"])
        self._win_recorded = False
        self.board.set_controller(self.controller)
        self._update_status()

    def puzzle_hint(self) -> None:
        if not self.puzzle:
            QMessageBox.information(self, "提示", "目前不在謎題模式。")
            return
        mv = self.puzzle["solution_first_move"]
        cell = "abcdefghij"[mv["col"]] + str(8 - mv["row"])
        kind = {"move": "移動", "swap": "換位", "rotate": "旋轉"}[mv["kind"]]
        QMessageBox.information(self, "提示", f"試試 {cell} 的棋子做「{kind}」。")

    # ------------------------------------------------------------ 背景計算
    def _maybe_start_ai(self) -> None:
        if (self.ai_difficulty is not None and not self.puzzle
                and self.controller.winner() is None
                and not self.controller.is_draw_by_repetition()
                and self.controller.state[0] == AI_COLOR):
            self._start_worker(self._compute_ai_move,
                               f"　AI（{AI_NAMES[self.ai_difficulty]}）思考中…")

    def _maybe_start_defender(self) -> None:
        """謎題模式：玩家走完換防守方（solver 最佳應手）。"""
        if (self.puzzle and self.controller.winner() is None
                and self.controller.state[0] != self.puzzle["player"]):
            self._start_worker(self._compute_defense, "　對手應手中…")

    def _start_worker(self, fn, status: str) -> None:
        self._token += 1
        self.board.input_locked = True
        self.status_label.setText(status)
        QThreadPool.globalInstance().start(_Worker(fn, self._token, self._signals))

    def _compute_ai_move(self):
        from khet.ai import choose_action
        return choose_action(self.controller.state, self.ai_difficulty,
                             history_counts=dict(self.controller.position_counts))

    def _compute_defense(self):
        from khet.puzzles import best_defense
        remaining = self.puzzle["difficulty"] - self.puzzle_moves_used
        return best_defense(self.controller.state, self.puzzle["player"],
                            max(1, remaining), timeout=10.0)

    def _on_worker_done(self, token: int, action) -> None:
        if token != self._token:            # 過期結果（新局/讀檔/悔棋後）丟棄
            return
        self.board.input_locked = False
        if (self.controller.winner() is not None
                or self.controller.is_draw_by_repetition()):
            return
        self.board.play_action(action)

    # ------------------------------------------------------------ 回合結束
    def _on_turn_finished(self, result) -> None:
        self._update_status()
        if self.puzzle:
            self._handle_puzzle_turn()
            return
        w = self.controller.winner()
        if w is not None:
            self._handle_game_over(w)
        elif self.controller.is_draw_by_repetition():
            play_sound("lose")
            QMessageBox.information(self, "和局", "同一局面第三次出現——依規則判和。")
        else:
            self._maybe_start_ai()

    def _handle_puzzle_turn(self) -> None:
        # turn_finished 在玩家或防守方走完後都會觸發；用當前輪到誰區分
        just_moved_was_player = (self.controller.state[0] != self.puzzle["player"])
        w = self.controller.winner()
        if w == self.puzzle["player"]:
            play_sound("win")
            user_data.mark_puzzle_solved(self.data, self.puzzle["id"])
            self._puzzle_finished(True)
            return
        if w is not None:                   # 玩家把自己走死了
            play_sound("lose")
            self._puzzle_finished(False)
            return
        if just_moved_was_player:
            self.puzzle_moves_used += 1
            if self.puzzle_moves_used >= self.puzzle["difficulty"]:
                # 手數用盡仍未獲勝 = 失敗
                play_sound("lose")
                self._puzzle_finished(False)
                return
            self._maybe_start_defender()

    def _puzzle_finished(self, solved: bool) -> None:
        pid = self.puzzle["id"]
        n = self.puzzle["difficulty"]
        self.puzzle = None
        box = QMessageBox(self)
        box.setWindowTitle("謎題結果")
        box.setText(f"謎題 {pid}（{DIFFICULTY_NAMES[n]}）\n\n"
                    + ("🎉 破解成功！" if solved else "❌ 未能在步數內獲勝。"))
        retry = box.addButton("重試", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("關閉", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == retry:
            from gui.puzzles_data import load_catalog
            for p in load_catalog():
                if p["id"] == pid:
                    self.start_puzzle(p)
                    return

    def _handle_game_over(self, w: str) -> None:
        if not self._win_recorded:
            self._win_recorded = True
            if self.ai_difficulty is not None:
                if w == AI_COLOR:
                    user_data.record_win(self.data, "ai_lost")
                else:
                    user_data.record_win(self.data, f"ai_{self.ai_difficulty}")
            else:
                user_data.record_win(self.data, f"hotseat_{w}")
        won_by_human = (self.ai_difficulty is None or w != AI_COLOR)
        play_sound("win" if won_by_human else "lose")
        box = QMessageBox(self)
        box.setWindowTitle("勝負揭曉")
        if self.ai_difficulty is not None:
            text = "你獲勝了！" if w != AI_COLOR else f"AI（{AI_NAMES[self.ai_difficulty]}）獲勝！"
        else:
            text = f"{COLOR_NAMES[w]} 獲勝！"
        box.setText(text)
        again = box.addButton("再來一局", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("關閉", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == again:
            self.new_game(self.controller.layout)

    def _update_status(self) -> None:
        player, _ = self.controller.state
        if self.puzzle:
            n = self.puzzle["difficulty"]
            left = n - self.puzzle_moves_used
            mode = (f"謎題 {self.puzzle['id']}（{DIFFICULTY_NAMES[n]}）"
                    f"　剩餘步數：{left}")
            you = f"你執 {COLOR_NAMES[self.puzzle['player']]}"
        else:
            mode = ("雙人對戰" if self.ai_difficulty is None
                    else f"人機對戰（AI：{AI_NAMES[self.ai_difficulty]}）")
            you = f"第 {self.controller.ply_count + 1} 手"
        self.status_label.setText(
            f"　{mode}　｜　輪到：{COLOR_NAMES[player]}　｜　{you}")
