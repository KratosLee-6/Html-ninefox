"""v0.8.2 设计 token 体检（源码静态统计，不依赖浏览器）。

输出四组数字，作为 B2 的验收依据与 B5-1 契约门禁的数据源：
  1. 字阶：字号 token 的定义值，以及工作台外壳里 <11px 的字面量
  2. 圆角：所有取值与出现次数
  3. 颜色：`:root` 之外的十六进制（工作台外壳）
  4. 间距：padding/margin/gap 里脱离 4/8 网格的字面量

用法：
    .venv/Scripts/python.exe scripts/design_tokens_report.py [--json out.json]

`--check` 时按契约阈值判定，非 0 退出（给 CI / 发布前用）。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"

# 工作台外壳 = 这几个文件；motion-lab.html 是设计实验室页，单独登记为豁免。
SHELL = {
    "index.html": STATIC / "index.html",
    "workbench-system.css": STATIC / "workbench-system.css",
}
EXEMPT = {"motion-lab.html": "设计实验室页（独立文档，自带一套演示配色）"}

FS_TOKEN = re.compile(r"--fs-(2xs|xs|sm|md|lg|xl|dsp):\s*(\d+)px")
FS_LITERAL = re.compile(r"font-size:\s*(\d+)px")
RADIUS = re.compile(r"border-radius:\s*([0-9.]+)(px|%)")
HEX = re.compile(r"#([0-9A-Fa-f]{6})\b")
SPACING = re.compile(r"(?:padding|margin|gap)(?:-[a-z]+)?:\s*([^;{}]+)")
ROOT_BLOCK = re.compile(r":root[^{]*\{(.*?)\}", re.S)
GRID = {0, 1, 2, 4, 8, 12, 16, 24, 32, 48, 64}


def _root_span(text: str) -> tuple[int, int]:
    """`:root { … }`（含双主题）在文件里的字符区间，用于把 token 定义排除在外。"""
    spans = []
    for match in ROOT_BLOCK.finditer(text):
        spans.append((match.start(), match.end()))
    return spans  # type: ignore[return-value]


def _outside_root(text: str, pattern: re.Pattern[str]) -> list[str]:
    spans = [s for s in _root_span(text)] or []
    hits = []
    for match in pattern.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        hits.append(match.group(0))
    return hits


def audit() -> dict:
    report: dict = {"files": {}, "totals": {}}
    for name, path in SHELL.items():
        text = path.read_text(encoding="utf-8")
        fonts = {f"--fs-{k}": int(v) for k, v in FS_TOKEN.findall(text)}
        literals = [int(v) for v in FS_LITERAL.findall(text)]
        small = sorted(v for v in literals if v < 11)
        radii = Counter(f"{v}{u}" for v, u in RADIUS.findall(text))
        hexes = Counter(h.upper() for h in _outside_root(text, HEX))

        off_grid = Counter()
        for chunk in SPACING.findall(text):
            for value in re.findall(r"(\d+)px", chunk):
                px = int(value)
                if px not in GRID and px > 2:
                    off_grid[px] += 1

        report["files"][name] = {
            "font_tokens": fonts,
            "font_literals_below_11": small,
            "radius": dict(sorted(radii.items())),
            "hex_outside_root": dict(sorted(hexes.items())),
            "spacing_off_grid": dict(sorted(off_grid.items())),
        }

    small_total = sum(len(f["font_literals_below_11"]) for f in report["files"].values())
    hex_total = sum(len(f["hex_outside_root"]) for f in report["files"].values())
    radii = Counter()
    off = Counter()
    for f in report["files"].values():
        radii.update(f["radius"])
        off.update(f["spacing_off_grid"])
    report["totals"] = {
        "font_literals_below_11": small_total,
        "hex_outside_root": hex_total,
        "radius_values": sorted(radii),
        "spacing_off_grid": dict(sorted(off.items())),
        "spacing_off_grid_count": sum(off.values()),
        "exempt": EXEMPT,
    }
    return report


def _whitelisted_hexes() -> dict[str, set[str]]:
    """契约里登记过的非 CSS 十六进制（meta theme-color、输入框示例值）。"""
    path = ROOT / "docs" / "design-contract.json"
    if not path.is_file():
        return {}
    contract = json.loads(path.read_text(encoding="utf-8"))
    allowed: dict[str, set[str]] = {}
    for entry in contract.get("color", {}).get("whitelist", []):
        allowed.setdefault(Path(entry["file"]).name, set()).add(entry["value"].upper())
    return allowed


def check(report: dict) -> list[str]:
    problems = []
    t = report["totals"]
    whitelist = _whitelisted_hexes()
    if t["font_literals_below_11"]:
        problems.append(f"工作台仍有 {t['font_literals_below_11']} 处 <11px 字面量")
    for name, f in report["files"].items():
        for token, value in f["font_tokens"].items():
            if token in {"--fs-xs", "--fs-2xs"} and value < 11:
                problems.append(f"{name}: {token}={value}px 低于 11px 下限")
        bad_radius = [r for r in f["radius"] if r not in {"3px", "4px", "5px", "6px", "999px", "50%"}]
        if bad_radius:
            problems.append(f"{name}: 圆角出现契约外取值 {bad_radius}")
        leftover = set(f["hex_outside_root"]) - whitelist.get(name, set())
        if leftover:
            problems.append(f"{name}: :root 之外有未登记十六进制 {sorted(leftover)}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.8.2 设计 token 体检")
    parser.add_argument("--json", type=Path, help="把结果写成 JSON")
    parser.add_argument("--check", action="store_true", help="按契约阈值判定，非 0 退出")
    args = parser.parse_args()

    report = audit()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, data in report["files"].items():
        print(f"[{name}]")
        print("  font tokens   :", data["font_tokens"])
        print("  <11px 字面量  :", data["font_literals_below_11"] or "无")
        print("  radius        :", data["radius"])
        print("  hex (:root 外):", data["hex_outside_root"] or "无")
        print("  脱网格间距    :", data["spacing_off_grid"] or "无")
    print("[totals]", json.dumps(report["totals"], ensure_ascii=False))

    problems = check(report)
    if problems:
        print("\n契约未达成：")
        for item in problems:
            print("  -", item)
        return 1 if args.check else 0
    print("\n契约通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
