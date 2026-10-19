"""Check the newest adopted artifact for placeholder/copy regressions."""

from __future__ import annotations

import glob
from pathlib import Path

root = Path(r"C:/Users/Admin/AppData/Local/Temp/fox082/output")
newest = sorted(root.glob("html9n-*"))[-1]
html = (newest / "output.html").read_text(encoding="utf-8")
print("dir:", newest.name, "chars:", len(html))
for token in ("Your Product", "更新目录", "本文档说明项目的背景"):
    hits = [i for i in range(len(html)) if html.startswith(token, i)]
    print(f"{token!r}:", len(hits))
    for i in hits[:3]:
        print("   ...", html[max(0, i - 90):i + 60].replace("\n", " "))
