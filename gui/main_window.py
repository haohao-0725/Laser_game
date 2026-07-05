"""主視窗：選單、狀態列、勝負/和局處理。"""
import os

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷射對決 Laser Duel（開發版）")
        icon_path = os.path.join(ASSETS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.controller = GameController("classic")
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

        help_menu = self.menuBar().addMenu("說明(&H)")
        rules_act = QAction("遊戲規則(&R)", self)
        rules_act.triggered.connect(self.show_rules)
        help_menu.addAction(rules_act)

    # ------------------------------------------------------------ 動作
    def new_game(self, layout: str) -> None:
        self.controller = GameController(layout)
        self.board.set_controller(self.controller)
        self._update_status()

    def undo(self) -> None:
        if self.board.mode == "animating":
            return
        self.controller.undo(1)
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
            self.controller = GameController.load(path)
        except Exception as exc:            # 壞檔要報錯而不是閃退
            QMessageBox.warning(self, "讀檔失敗", f"無法載入存檔：\n{exc}")
            return
        self.board.set_controller(self.controller)
        self._update_status()

    def show_rules(self) -> None:
        QMessageBox.information(self, "遊戲規則", RULES_TEXT)

    # ------------------------------------------------------------ 回合結束
    def _on_turn_finished(self, result) -> None:
        self._update_status()
        w = self.controller.winner()
        if w is not None:
            box = QMessageBox(self)
            box.setWindowTitle("勝負揭曉")
            box.setText(f"{COLOR_NAMES[w]} 獲勝！")
            again = box.addButton("再來一局", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("關閉", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == again:
                self.new_game(self.controller.layout)
        elif self.controller.is_draw_by_repetition():
            QMessageBox.information(self, "和局", "同一局面第三次出現——依規則判和。")

    def _update_status(self) -> None:
        player, _ = self.controller.state
        self.status_label.setText(
            f"　輪到：{COLOR_NAMES[player]}　｜　第 {self.controller.ply_count + 1} 手"
            f"　｜　佈局：{LAYOUT_NAMES[self.controller.layout]}"
            f"　｜　點自己的棋子 → 點綠圈移動／紫圈換位／⟳ 旋轉")
