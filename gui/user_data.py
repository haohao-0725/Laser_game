"""使用者資料持久化：設定（音效開關）、戰績（勝場）、謎題通關記錄。
存到 %APPDATA%\\LaserDuel\\user_data.json（無 %APPDATA% 時退回家目錄）。無 Qt 依賴。"""
import json
import os

_APPDIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "LaserDuel")
_PATH = os.path.join(_APPDIR, "user_data.json")

_DEFAULT = {
    "sound_enabled": True,
    "wins": {"hotseat_SILVER": 0, "hotseat_RED": 0,
             "ai_easy": 0, "ai_medium": 0, "ai_hard": 0,
             "ai_lost": 0},
    "puzzles_solved": [],       # 已通關的 puzzle id 列表
}


def load() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return json.loads(json.dumps(_DEFAULT))     # 深複本
    # 補齊缺欄位（版本演進容錯）
    for k, v in _DEFAULT.items():
        data.setdefault(k, json.loads(json.dumps(v)))
    for k, v in _DEFAULT["wins"].items():
        data["wins"].setdefault(k, v)
    return data


def save(data: dict) -> None:
    try:
        os.makedirs(_APPDIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except OSError:
        pass                    # 存不了不該讓遊戲崩潰


def record_win(data: dict, key: str) -> None:
    data["wins"][key] = data["wins"].get(key, 0) + 1
    save(data)


def mark_puzzle_solved(data: dict, pid: str) -> None:
    if pid not in data["puzzles_solved"]:
        data["puzzles_solved"].append(pid)
        save(data)
