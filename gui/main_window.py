"""主視窗：選單、狀態列、勝負/和局處理、人機對戰（AI 背景執行緒）。"""
import os

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QFileDialog, QLabel, QMainWindow, QMessageBox,
)

from gui.assets import ASSETS_DIR
from gui.board_widget import BoardWidget
from gui.game_controller import GameController

LAYOUT_NAMES = {"classic": "經典（Classic）",
                "imhotep": "印和闐（Imhotep）",
                "dynasty": "王朝（Dynasty）"}
COLOR_NAMES = {"SILVER": "銀方", "RED": "紅方"}
AI_NAMES = {"easy": "簡單", "medium": "中等", "hard": "困難"}
AI_COLOR = "RED"            # AI 固定執紅（後手），玩家執銀先手

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


class _AISignals(QObject):
    done = pyqtSignal(int, object)      # (token, action)


class _AITask(QRunnable):
    def __init__(self, state, difficulty: str, token: int, signals: _AISignals,
                 history_counts: dict | None = None):
        super().__init__()
        self.state = state
        self.difficulty = difficulty
        self.token = token
        self.signals = signals
        self.history_counts = history_counts

    def run(self) -> None:
        from khet.ai import choose_action
        action = choose_action(self.state, self.difficulty,
                               history_counts=self.history_counts)
        self.signals.done.emit(self.token, action)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷射對決 Laser Duel（開發版）")
        icon_path = os.path.join(ASSETS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.controller = GameController("classic")
        self.ai_difficulty: str | None = None      # None = 雙人對戰
        self._ai_token = 0
        self._ai_signals = _AISignals()
        self._ai_signals.done.connect(self._on_ai_done)
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

        help_menu = self.menuBar().addMenu("說明(&H)")
        rules_act = QAction("遊戲規則(&R)", self)
        rules_act.triggered.connect(self.show_rules)
        help_menu.addAction(rules_act)

    # ------------------------------------------------------------ 模式與對局
    def set_ai_mode(self, difficulty: str | None) -> None:
        self.ai_difficulty = difficulty
        self.new_game(self.controller.layout)

    def new_game(self, layout: str) -> None:
        self._ai_token += 1                 # 作廢所有進行中的 AI 計算結果
        self.controller = GameController(layout)
        self.board.set_controller(self.controller)
        self._update_status()

    def undo(self) -> None:
        if self.board.mode == "animating" or self.board.input_locked:
            return
        # 人機模式退 2 手（把 AI 那手一起退掉），雙人模式退 1 手
        self.controller.undo(2 if self.ai_difficulty else 1)
        self.board.selected = None
        self.board.overlay = []
        self.board.mode = "idle"
        self.board.update()
        self._update_status()

    def save_game(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "存檔", "khet_save.json", "Khet 存檔 (*.json)")
        if path:
            self.controller.save(path)
            self.statusBar().showMessage(f"已存檔：{path}", 4000)

    def load_game(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "讀檔", "", "Khet 存檔 (*.json)")
        if not path:
            return
        try:
            controller = GameController.load(path)
        except Exception as exc:            # 壞檔要報錯而不是閃退
            QMessageBox.warning(self, "讀檔失敗", f"無法載入存檔：\n{exc}")
            return
        self._ai_token += 1
        self.controller = controller
        self.board.set_controller(self.controller)
        self._update_status()
        self._maybe_start_ai()

    def show_rules(self) -> None:
        QMessageBox.information(self, "遊戲規則", RULES_TEXT)

    # ------------------------------------------------------------ AI 回合
    def _maybe_start_ai(self) -> None:
        if (self.ai_difficulty is not None
                and self.controller.winner() is None
                and not self.controller.is_draw_by_repetition()
                and self.controller.state[0] == AI_COLOR):
            self._ai_token += 1
            self.board.input_locked = True
            self.status_label.setText(f"　AI（{AI_NAMES[self.ai_difficulty]}）思考中…")
            task = _AITask(self.controller.state, self.ai_difficulty,
                           self._ai_token, self._ai_signals,
                           dict(self.controller.position_counts))  # 複本，避免跨執行緒共享
            QThreadPool.globalInstance().start(task)

    def _on_ai_done(self, token: int, action) -> None:
        if token != self._ai_token:         # 過期結果（新局/讀檔/悔棋後）直接丟棄
            return
        self.board.input_locked = False
        self.board.play_action(action)

    # ------------------------------------------------------------ 回合結束
    def _on_turn_finished(self, result) -> None:
        self._update_status()
        w = self.controller.winner()
        if w is not None:
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
            return
        if self.controller.is_draw_by_repetition():
            QMessageBox.information(self, "和局", "同一局面第三次出現——依規則判和。")
            return
        self._maybe_start_ai()

    def _update_status(self) -> None:
        player, _ = self.controller.state
        mode = ("雙人對戰" if self.ai_difficulty is None
                else f"人機對戰（AI：{AI_NAMES[self.ai_difficulty]}）")
        self.status_label.setText(
            f"　{mode}　｜　輪到：{COLOR_NAMES[player]}　｜　第 {self.controller.ply_count + 1} 手"
            f"　｜　佈局：{LAYOUT_NAMES[self.controller.layout]}")
