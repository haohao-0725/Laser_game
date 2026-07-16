"""以 package.json 為 Android 版本單一來源，供 gitignore 的 android/ 重生後套用。"""
from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version_name = package["version"]
    version_code = int(package["androidVersionCode"])
    gradle_path = ROOT / "android" / "app" / "build.gradle"
    if not gradle_path.exists():
        raise SystemExit("找不到 android/app/build.gradle；請先執行 npx cap add/sync android")

    source = gradle_path.read_text(encoding="utf-8")
    source, code_count = re.subn(
        r"(?m)^(\s*versionCode\s+)\d+\s*$",
        rf"\g<1>{version_code}",
        source,
    )
    source, name_count = re.subn(
        r'(?m)^(\s*versionName\s+)"[^"]*"\s*$',
        rf'\g<1>"{version_name}"',
        source,
    )
    if code_count != 1 or name_count != 1:
        raise SystemExit("build.gradle 的 versionCode/versionName 格式不符合預期")
    gradle_path.write_text(source, encoding="utf-8")
    print(f"Android 版本：versionCode={version_code}, versionName={version_name}")


if __name__ == "__main__":
    main()
