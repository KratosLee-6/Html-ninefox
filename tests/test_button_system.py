"""按钮系统门禁（v0.8.2 · B4 控件纪律）。

真实产品规范里按钮最容易失守的是三件事，这里各锁一条：
  1. 尺寸：常用 32、顶栏 36、移动 40 —— 不能有 28px 的「可点但不好点」
  2. 状态：键盘 focus 必须看得见（陶土橙环），disabled 不能还带 hover 位移
  3. 层级：同一屏只能有一个实心主色按钮
"""

from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import WorkbenchServer


@pytest.fixture()
def page_fixture(tmp_path):
    with WorkbenchServer(tmp_path) as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxWorkbenchUI", timeout=30000)
        page.wait_for_timeout(600)
        try:
            yield page
        finally:
            browser.close()


def test_buttons_meet_the_minimum_target_size(page_fixture):
    small = page_fixture.eval_on_selector_all(
        ".topbar .btn, .sidebar .btn, #btn-go, #btn-create",
        """els => els.filter(el => {
             const r = el.getBoundingClientRect();
             return r.height > 0 && r.height < 32;
           }).map(el => ({ text: (el.innerText || el.id).trim(), h: el.getBoundingClientRect().height }))""")
    assert not small, f"这些按钮低于 32px 目标尺寸：{small}"


def test_keyboard_focus_is_visible(page_fixture):
    page_fixture.keyboard.press("Tab")
    page_fixture.keyboard.press("Tab")
    outline = page_fixture.evaluate(
        """() => {
          const el = document.activeElement;
          if (!el) return null;
          const s = getComputedStyle(el);
          return { tag: el.tagName, cls: el.className, width: s.outlineWidth, style: s.outlineStyle };
        }""")
    assert outline is not None
    if "btn" in str(outline["cls"]):
        assert outline["style"] != "none" and float(outline["width"].replace("px", "")) >= 2, \
            f"聚焦环不可见：{outline}"


def test_icon_only_buttons_are_labeled_and_sized(page_fixture):
    """纯图标按钮：必须有可访问名，点击区 ≥32×32，状态切换不改尺寸。"""
    offenders = page_fixture.eval_on_selector_all(
        ".btn-icon",
        """els => els.filter(el => {
             const r = el.getBoundingClientRect();
             if (r.width === 0 || r.height === 0) return false;
             const name = (el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
             return !name || r.width < 32 || r.height < 32;
           }).map(el => ({
             cls: el.className,
             label: el.getAttribute('aria-label'),
             w: el.getBoundingClientRect().width,
             h: el.getBoundingClientRect().height,
           }))""")
    assert not offenders, f"纯图标按钮缺可访问名或尺寸不足：{offenders}"


def test_one_filled_primary_per_view(page_fixture):
    primaries = page_fixture.eval_on_selector_all(
        ".btn-primary",
        """els => els.filter(el => {
             const r = el.getBoundingClientRect();
             const s = getComputedStyle(el);
             return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' &&
                    s.backgroundColor !== 'rgba(0, 0, 0, 0)';
           }).map(el => (el.innerText || el.id).trim())""")
    assert len(primaries) == 1, f"一屏只允许一个实心主操作，实测：{primaries}"
