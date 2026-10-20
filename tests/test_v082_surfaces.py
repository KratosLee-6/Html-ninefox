"""v0.8.2 面层与尺度门禁（B3-5 / B4-2 / B4-4）。

三条：
  1. 检查器空态必须是「一句话 + 三个能点的起点」，不是说明书
  2. 图标只有 16 / 20 两档，线宽 1.8
  3. 像素投影只许留在选中节点与主按钮（按选择器白名单判定，不数行数）
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"

PIXEL_SHADOW = re.compile(r"box-shadow:\s*[^;]*?\b[234]px\s+[234]px\s+0\b")
ALLOWED = (".btn-primary", "--shadow:")  # 主按钮；节点选中的投影 token 定义


@pytest.fixture
def workbench(workbench_server):
    with workbench_server as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            try:
                page.goto(server.base_url)
                page.wait_for_function("window.FoxMotion && nodes.length >= 4")
                yield page, server.base_url
                assert not errors, errors
            finally:
                browser.close()


def test_inspector_empty_state_offers_three_starting_points(workbench):
    page, _ = workbench
    # 不点任何东西：第一屏（静态 HTML 直出）就必须已经是新空态
    page.wait_for_timeout(250)

    panel = page.locator("#inspector")
    text = panel.inner_text()
    buttons = panel.locator(".ins-empty-actions .btn")

    assert "还没选中任何东西" in text
    assert buttons.count() == 3, f"空态应该给三个起点，实际 {buttons.count()}"
    labels = [buttons.nth(i).inner_text().strip() for i in range(3)]
    assert labels == ["写一句需求", "补充素材", "新建工作区"], labels
    assert "选中节点查看属性" not in text, "旧的说明书文案还在"


def test_inspector_empty_actions_are_real_handlers(workbench):
    page, _ = workbench
    page.evaluate("window.FoxCanvas?.select?.(null)")
    page.wait_for_timeout(250)

    actions = page.evaluate(
        """() => [...document.querySelectorAll('#inspector .ins-empty-actions [data-action]')]
                   .map(el => el.dataset.action)""")

    assert actions == ["openCreatePanel", "openIntake", "addWorkspace"], actions
    page.click('#inspector .ins-empty-actions [data-action="openCreatePanel"]')
    page.wait_for_timeout(350)
    opened = page.evaluate(
        """() => ['#create-modal', '#create-panel', '#composer', '#intake-dialog', '.modal:not([hidden])']
             .some(sel => {
               const el = document.querySelector(sel);
               if (!el || el.hasAttribute('hidden')) return false;
               const r = el.getBoundingClientRect();
               return r.width > 0 && r.height > 0;   // 弹窗是 position:fixed，offsetParent 恒为 null
             })""")
    assert opened, "点了「写一句需求」却没有任何面板打开"


def test_icons_are_16_or_20_with_one_stroke(workbench):
    page, _ = workbench
    odd = page.evaluate(
        """() => [...document.querySelectorAll('.ui-icon')]
             .filter(el => el.getBoundingClientRect().width > 0)
             .map(el => {
               const s = getComputedStyle(el);
               return { w: parseFloat(s.width), stroke: s.strokeWidth };
             })
             .filter(x => ![16, 20].includes(x.w) || x.stroke !== '1.8px')""")

    assert not odd, f"图标只允许 16/20 两档、线宽 1.8：{odd[:6]}"


def test_pixel_shadow_only_on_the_two_surfaces():
    offenders = []
    for name in ("index.html", "workbench-system.css"):
        text = (STATIC / name).read_text(encoding="utf-8")
        # 按规则块判定：选择器允许主按钮，或这是 --shadow 这个投影 token 的定义
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            selector, body = match.group(1).strip(), match.group(2)
            if not PIXEL_SHADOW.search(body):
                continue
            if ".btn-primary" in selector or "--shadow:" in body:
                continue
            offenders.append(f"{name}: {selector[:60]}")

    assert not offenders, f"像素投影只许留在选中节点与主按钮：{offenders}"


def test_no_action_is_a_placeholder_stub():
    """动作表里不许出现 `xxx: (...) => undefined`。

    真事：编辑检查器模板时把 `openExportCenter` 改成了这样，导出按钮全变死，
    静态检查与单测都还是绿的，只有端到端导出用例会红。
    """
    text = (STATIC / "fox-core.js").read_text(encoding="utf-8")
    stubs = re.findall(r"^\s*(\w+)\s*:\s*(?:\([^)]*\)|\w+)\s*=>\s*undefined\s*,?\s*$",
                       text, re.MULTILINE)
    assert not stubs, f"这些动作只剩占位 stub，点了不会有反应：{stubs}"
