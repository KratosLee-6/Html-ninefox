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


def test_contract_records_layout_rules_for_the_next_batch():
    """B3 的门禁还没接上，但规则先落纸，避免下一批人重新定义。"""
    layout = CONTRACT["layout"]

    assert layout["primary_cta_per_screen"] == 1
    assert layout["max_border_layers"] <= 2
    assert layout["empty_state_requires_action"] is True
