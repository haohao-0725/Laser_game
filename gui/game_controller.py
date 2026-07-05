"""對局管理：歷史堆疊（悔棋）、三次同形偵測、重放式存讀檔。無 Qt 依賴（可單元測試）。"""
import json

from khet.engine import (
    action_from_dict, action_to_dict,          # re-export（序列化的權威在引擎層）
    apply_action, initial_state, winner as engine_winner,
)


class GameController:
    def __init__(self, layout: str = "classic"):
        self.layout = layout
        self.state = initial_state(layout)
        self.history = [self.state]          # 歷代 state（含初始）
        self.actions_done: list = []          # 已執行的 action（存檔用）
        self.position_counts = {self.state: 1}

    @classmethod
    def from_state(cls, state: tuple) -> "GameController":
        """從任意局面開局（謎題模式用）。此模式不支援重放式存檔。"""
        gc = cls.__new__(cls)
        gc.layout = "custom"
        gc.state = state
        gc.history = [state]
        gc.actions_done = []
        gc.position_counts = {state: 1}
        return gc

    # ---------------------------------------------------------- 對局操作
    def do_action(self, action):
        """執行一手（含強制雷射），回傳 LaserResult。"""
        new_state, result = apply_action(self.state, action)
        self.state = new_state
        self.history.append(new_state)
        self.actions_done.append(action)
        self.position_counts[new_state] = self.position_counts.get(new_state, 0) + 1
        return result

    def undo(self, plies: int = 1) -> bool:
        """退 plies 手（hotseat 退 1、對 AI 退 2）。退到初始為止。"""
        done = False
        for _ in range(plies):
            if len(self.history) <= 1:
                break
            popped = self.history.pop()
            self.position_counts[popped] -= 1
            self.actions_done.pop()
            self.state = self.history[-1]
            done = True
        return done

    # ---------------------------------------------------------- 狀態查詢
    def winner(self):
        return engine_winner(self.state)

    def is_draw_by_repetition(self) -> bool:
        return self.position_counts.get(self.state, 0) >= 3

    @property
    def ply_count(self) -> int:
        return len(self.actions_done)

    # ---------------------------------------------------------- 存讀檔（重放式）
    def save(self, path: str) -> None:
        data = {
            "format": "khet-replay-v1",
            "layout": self.layout,
            "actions": [action_to_dict(a) for a in self.actions_done],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    @classmethod
    def load(cls, path: str) -> "GameController":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("format") != "khet-replay-v1":
            raise ValueError("不支援的存檔格式")
        gc = cls(data["layout"])
        for d in data["actions"]:
            gc.do_action(action_from_dict(d))
        return gc
