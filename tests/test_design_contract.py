"""设计契约门禁（v0.8.2 · B5-1）。

手册写在 markdown 里，代码写在 CSS 里，两边都没有门禁的时候，三个版本就能
把手册写旧（v0.8.0 之前的实况）。这里把 `docs/design-contract.json` 变成唯一
数值来源，做三件事：

  1. 代码里的 token 值必须与契约一致（改了代码不改契约 → 红）
  2. 契约里的每个 token 必须真的在 CSS 里（删了代码不改契约 → 红）
  3. 契约的硬规则（最小字号 / 圆角集合 / 裸 hex / 间距不变差）必须成立
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import design_tokens_report as report_mod  # noqa: E402  (脚本即数据源，避免两套统计)

CONTRACT = json.loads((ROOT / "docs" / "design-contract.json").read_text(encoding="utf-8"))
CSS = ROOT / "htmlninefox" / "server" / "static" / "workbench-system.css"


def test_contract_file_is_in_scope_and_versioned():
    assert CONTRACT["version"] >= 1
    assert CONTRACT["scope"]["shell"], "契约必须声明作用域文件"
    for relative in CONTRACT["scope"]["shell"]:
        assert (ROOT / relative).is_file(), relative


def test_code_tokens_match_the_contract_exactly():
    report = report_mod.audit()
    declared = CONTRACT["font"]["scale"]

    for name, data in report["files"].items():
        for token, value in data["font_tokens"].items():
            assert token in declared, f"{name} 出现了契约外字号 token：{token}"
            assert value == declared[token], f"{name} {token}={value}px，契约写 {declared[token]}px"


def test_every_contract_token_exists_in_css():
    text = CSS.read_text(encoding="utf-8")
    for token, value in CONTRACT["font"]["scale"].items():
        assert f"{token}:{value}px" in text or f"{token}: {value}px" in text, token


def test_minimum_font_size_holds():
    report = report_mod.audit()
    floor = CONTRACT["font"]["min_px"]

    assert report["totals"]["font_literals_below_11"] == 0
    for name, data in report["files"].items():
        for token, value in data["font_tokens"].items():
            assert value >= floor, f"{name} {token}={value}px 低于 {floor}px"


def test_radius_stays_inside_the_scale():
    report = report_mod.audit()
    allowed = {f"{v}px" for v in CONTRACT["radius"]["allowed_px"]}
    allowed.add(f"{CONTRACT['radius']['pill_px']}px")
    allowed.update(CONTRACT["radius"]["extra_allowed"])

    for name, data in report["files"].items():
        outside = sorted(set(data["radius"]) - allowed)
        assert not outside, f"{name} 圆角出现契约外取值：{outside}"


def test_no_bare_hex_outside_the_whitelist():
    report = report_mod.audit()
    whitelist = {}
    for entry in CONTRACT["color"]["whitelist"]:
        whitelist.setdefault(Path(entry["file"]).name, set()).add(entry["value"].upper())

    for name, data in report["files"].items():
        leftover = set(data["hex_outside_root"]) - whitelist.get(name, set())
        assert not leftover, f"{name} 仍有未登记的十六进制：{sorted(leftover)}"


def test_spacing_does_not_get_worse():
    """B2-2 是分批收口；在它完成前，这条只保证「不再变差」。"""
    report = report_mod.audit()
    baseline = CONTRACT["spacing"]["off_grid_baseline"]
    count = report["totals"]["spacing_off_grid_count"]

    assert count <= baseline, (
        f"脱网格间距从 {baseline} 涨到 {count} —— 新增的间距请走 --space-* token")


def test_display_serif_is_actually_used():
    """B4-1：衬线不能只写在契约里，至少三处选择器要真的用它。"""
    import re as _re

    css = (ROOT / "htmlninefox" / "server" / "static" / "workbench-system.css").read_text(encoding="utf-8")
    html = (ROOT / "htmlninefox" / "server" / "static" / "index.html").read_text(encoding="utf-8")
    display = CONTRACT["font"]["display_serif"]

    assert display["token"] in html, "衬线 token 必须定义在 :root"
    # 一条规则里可以并列多个选择器，所以数选择器，不数 var() 出现次数。
    selectors = 0
    for block in _re.findall(r"([^{}]+)\{[^{}]*var\(%s\)[^{}]*\}" % _re.escape(display["token"]), css):
        selectors += len([part for part in block.split(",") if part.strip()])
    assert selectors >= display["min_selectors"], \
        f"衬线只覆盖 {selectors} 个选择器，契约要求 ≥{display['min_selectors']}"


def test_focus_ring_meets_non_text_contrast():
    """焦点环必须 ≥3:1（WCAG 1.4.11）。陶土橙 2.87:1 不合格，已改钴蓝 9.92:1。"""
    import re as _re

    html = (ROOT / "htmlninefox" / "server" / "static" / "index.html").read_text(encoding="utf-8")
    tokens = dict(_re.findall(r"(--[a-z0-9-]+):(#?[0-9A-Za-z()%,.\s-]+);", html))

    def hex_of(token: str) -> str:
        value = tokens[token].strip()
        assert value.startswith("#") and len(value) == 7, f"{token} 不是十六进制：{value}"
        return value

    def luminance(value: str) -> float:
        raw = value.lstrip("#")
        channels = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                  for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(a: str, b: str) -> float:
        la, lb = luminance(a), luminance(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    ring = hex_of("--focus-ring")
    for surface in ("--bg-panel", "--bg-base"):
        ratio = contrast(ring, hex_of(surface))
        assert ratio >= 3.0, f"焦点环 {ring} 对 {surface} 只有 {ratio:.2f}:1，低于 3:1"


def test_every_used_custom_property_is_defined():
    """`var(--x)` 写错名字不会报错，只会静默 fallback 成透明/继承色。

    真实案例：`.template-badge` 用了 `--surface-raised`，该 token 从未定义，
    夜蓝主题下徽标背景变透明，白字压在浅色缩略图上只剩 1.67:1。
    """
    static = ROOT / "htmlninefox" / "server" / "static"
    sources = [p for p in static.glob("*.css")] + [static / "index.html", static / "motion-system.js"]
    defined: set[str] = set()
    used: dict[str, str] = {}

    for path in sources:
        text = path.read_text(encoding="utf-8")
        defined.update(re.findall(r"(--[a-z0-9-]+)\s*:", text))
        for match in re.finditer(r"var\(\s*(--[a-z0-9-]+)\s*([,)])", text):
            name, tail = match.group(1), match.group(2)
            if tail == ",":      # 自带兜底值的可以不全局定义
                continue
            used.setdefault(name, path.name)

    missing = {name: origin for name, origin in used.items() if name not in defined}
    assert not missing, f"这些自定义属性从未定义（会静默失效）：{missing}"


def test_no_self_referential_tokens():
    """`--focus:var(--focus)` 这类自引用会让 token 变成空值，界面上还看不出来。

    这是真发生过的：批量把十六进制换成 var(--token) 时，把定义那一行也换了，
    结果焦点环颜色变成 currentColor、对比度全线静默下降。
    """
    import re as _re

    html = (ROOT / "htmlninefox" / "server" / "static" / "index.html").read_text(encoding="utf-8")
    pairs = _re.findall(r"(--[a-z0-9-]+)\s*:\s*var\((--[a-z0-9-]+)\)", html)
    self_refs = sorted({name for name, target in pairs if name == target})
    assert not self_refs, f"这些 token 定义成了自己：{self_refs}"


def test_contract_records_layout_rules_for_the_next_batch():
    """B3 的门禁还没接上，但规则先落纸，避免下一批人重新定义。"""
    layout = CONTRACT["layout"]

    assert layout["primary_cta_per_screen"] == 1
    assert layout["max_border_layers"] <= 2
    assert layout["empty_state_requires_action"] is True
