"""把 data/*.json 打包成 www/js/rules_data.js（Python 與 JS 共用同一份規則資料）。
執行：.\\venv\\Scripts\\python.exe scripts\\export_web_data.py
禁止手寫 rules_data.js——一律由此生成，才能保證雙平台規則同源。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name: str) -> dict:
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    data = {
        "laser_table": load("laser_table.json")["table"],
        "layouts": load("layouts.json"),
        "puzzles": load("puzzle_catalog.json"),
    }
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    out = os.path.join(ROOT, "www", "js", "rules_data.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("// 由 scripts/export_web_data.py 生成，禁止手改。\n")
        f.write("(function(){\n")
        f.write(f"  var DATA = {body};\n")
        f.write("  if (typeof module !== 'undefined' && module.exports) module.exports = DATA;\n")
        f.write("  if (typeof window !== 'undefined') window.RULES_DATA = DATA;\n")
        f.write("})();\n")
    print(f"OK: 已寫出 {out}（{len(body)} bytes）")


if __name__ == "__main__":
    main()
