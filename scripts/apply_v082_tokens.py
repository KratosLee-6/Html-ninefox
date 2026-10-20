"""B2 收敛的机械部分：字阶下限、圆角刻度、裸色并入 token。

只做**可穷举**的三类改动，每一类都能用 design_tokens_report.py 复核：
  1. --fs-2xs / --fs-2xs 抬到 11px（工作台最小文字下限）
  2. border-radius 归到 {3,4,5,6,999,50%}
  3. :root 之外的十六进制换成 var(--token)，无法替换的（SVG 属性、输入框示例值）登记豁免

不做间距重排：2px 位移会改变呼吸，按计划分批单独提交。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"
CSS = STATIC / "workbench-system.css"
INDEX = STATIC / "index.html"

RADIUS_MAP = {"2": "3", "7": "6", "8": "6", "10": "6", "14": "6", "16": "6"}

HEX_MAP = {
    "#D35D5D": "var(--danger)",
    "#D35D5D".lower(): "var(--danger)",
    "#E57A3F": "var(--focus)",
    "#1f6f57": "var(--success)",
    "#3c4552": "var(--text-secondary)",
    "#5a6473": "var(--text-secondary)",
    "#e5e2d8": "var(--border-subtle)",
}


def rewrite_radius(text: str) -> tuple[str, int]:
    changed = 0

    def sub(match: re.Match[str]) -> str:
        nonlocal changed
        value = match.group(1)
        if value in RADIUS_MAP:
            changed += 1
            return f"border-radius:{RADIUS_MAP[value]}px"
        return match.group(0)

    return re.sub(r"border-radius:\s*(\d+)px", sub, text), changed


def rewrite_hex(text: str) -> tuple[str, int]:
    changed = 0
    for needle, token in HEX_MAP.items():
        pattern = re.compile(re.escape(needle))
        text, count = pattern.subn(token, text)
        changed += count
    return text, changed


def main() -> int:
    for path in (CSS, INDEX):
        text = path.read_text(encoding="utf-8")
        original = text

        if path is CSS:
            text = text.replace("--fs-2xs:9px", "--fs-2xs:11px")
            text = text.replace("--fs-xs:10px", "--fs-xs:11px")
            text = text.replace("font-size:10px", "font-size:11px")

        text, radius_changes = rewrite_radius(text)
        text, hex_changes = rewrite_hex(text)

        if text != original:
            path.write_text(text, encoding="utf-8", newline="")
        print(f"{path.name}: radius {radius_changes} 处 · hex {hex_changes} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
