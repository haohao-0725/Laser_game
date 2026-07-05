"""謎題目錄對話框：三難度分頁 × 題目清單，通關打勾；含「每日一題」。"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from gui.puzzles_data import DIFFICULTY_NAMES, daily_puzzle, load_catalog


class PuzzleDialog(QDialog):
    puzzle_chosen = pyqtSignal(object)      # 參數：puzzle dict

    def __init__(self, solved_ids: set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("謎題模式")
        self.resize(420, 480)
        self.puzzles = load_catalog()
        self.solved_ids = solved_ids
        layout = QVBoxLayout(self)

        if not self.puzzles:
            layout.addWidget(QLabel("尚無謎題目錄。\n請先執行 scripts/gen_puzzles.py 生成。"))
            return

        # 每日一題
        daily = daily_puzzle(self.puzzles)
        daily_btn = QPushButton(f"🌟 每日一題（{DIFFICULTY_NAMES[daily['difficulty']]}）")
        daily_btn.clicked.connect(lambda: self._choose(daily))
        layout.addWidget(daily_btn)

        solved_count = len(solved_ids & {p["id"] for p in self.puzzles})
        layout.addWidget(QLabel(f"目錄共 {len(self.puzzles)} 題，已通關 {solved_count} 題"))

        tabs = QTabWidget()
        for n in (1, 2, 3):
            group = [p for p in self.puzzles if p["difficulty"] == n]
            lst = QListWidget()
            for p in sorted(group, key=lambda x: x["id"]):
                mark = "✅ " if p["id"] in solved_ids else "◻ "
                item = QListWidgetItem(f"{mark}{p['id']}（{p['player']} 先手）")
                item.setData(Qt.ItemDataRole.UserRole, p)
                lst.addItem(item)
            lst.itemDoubleClicked.connect(
                lambda it: self._choose(it.data(Qt.ItemDataRole.UserRole)))
            tabs.addTab(lst, f"{DIFFICULTY_NAMES[n]}（{len(group)}）")
        layout.addWidget(tabs)
        self._tabs = tabs

        row = QHBoxLayout()
        play_btn = QPushButton("開始挑戰")
        play_btn.clicked.connect(self._play_selected)
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.reject)
        row.addWidget(play_btn)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _play_selected(self) -> None:
        lst = self._tabs.currentWidget()
        item = lst.currentItem()
        if item is not None:
            self._choose(item.data(Qt.ItemDataRole.UserRole))

    def _choose(self, puzzle) -> None:
        self.puzzle_chosen.emit(puzzle)
        self.accept()
