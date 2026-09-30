"""界面版式与信息层级的回归门禁。

这些断言锁住 2026-09-29 设计体检之后做的版面修正。它们都不是审美偏好，
而是可测量的版式事实——其中画布缩放那条曾经让内容缩到 0.33 倍、右侧
空出 666px，用户第一眼看到的是「这软件怎么这么小」。

尺度 token（字号 / 字重）的一致性由 test_design_health_gates.py 与
scripts/design_audit.py 覆盖；这里只管版面与信息层级。
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import sync_playwright

READY = "window.FoxWorkbenchUI && window.FoxIntake && nodes.length >= 1"


@pytest.fixture
def workbench(tmp_path):
    from tests.conftest import WorkbenchServer

    with WorkbenchServer(tmp_path) as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/")
        page.wait_for_function(READY, timeout=20000)
        page.wait_for_timeout(1200)   # 等首屏 fitAll 的 120ms 延迟执行完
        yield page, errors
        browser.close()


def test_canvas_does_not_reserve_a_full_height_left_band(workbench) -> None:
    """浮层工作区导航卡是左上角一块，不该按通高左栏预留。

    旧实现 `left: 导航卡右缘` 把 916px 画布的可用宽度压到 446px，
    缩放被逼到 0.33，内容缩成一小团、右侧空出 666px。
    """
    page, _ = workbench
    insets = page.evaluate("canvasFitInsets()")
    assert insets["left"] == 0, f"不应按通高左栏预留，实测 {insets}"
    # 其余三边应按浮层真实几何给出，且合计不得吃掉大半画布
    viewport_w = page.evaluate(
        "Math.round((document.querySelector('#viewport')||document.querySelector('.canvas-wrap')).getBoundingClientRect().width)")
    used = insets["left"] + insets["right"]
    assert used < viewport_w * 0.25, f"左右避让合计吃掉过多宽度：{insets} / 画布 {viewport_w}"


def test_first_load_zoom_is_usable(workbench) -> None:
    """首屏适配后的缩放要能读，而不是缩成缩略图。"""
    page, _ = workbench
    zoom = page.evaluate("camera.z")
    assert zoom >= 0.6, f"首屏缩放过小（{zoom:.2f}），内容会缩成一团看不清"


def test_canvas_content_uses_available_width(workbench) -> None:
    page, _ = workbench
    ratio = page.evaluate("""() => {
      const vp = document.querySelector('#viewport') || document.querySelector('.canvas-wrap');
      const r = vp.getBoundingClientRect();
      const ns = [...document.querySelectorAll('.node:not(.ws)')]
        .map(n => n.getBoundingClientRect());
      if (!ns.length) return 1;
      const L = Math.min(...ns.map(n => n.left)), R = Math.max(...ns.map(n => n.right));
      return (R - L) / r.width;
    }""")
    assert ratio >= 0.3, f"画布内容只占 {ratio:.0%} 宽度，右侧大片空置"


def test_template_cards_have_stable_height(workbench) -> None:
    """模板卡此前因英文描述与标题并排 flex 而高度跳到 179px、标题断词换行。"""
    page, _ = workbench
    cards = page.evaluate("""() => [...document.querySelectorAll('.pal-card')].map(c => {
      const zh = c.querySelector('.pal-name .zh');
      const en = c.querySelector('.pal-name .en');
      const lh = e => e ? parseFloat(getComputedStyle(e).lineHeight) : 0;
      return { h: Math.round(c.getBoundingClientRect().height),
               zhLines: zh && lh(zh) ? Math.round(zh.getBoundingClientRect().height / lh(zh)) : 0,
               enLines: en && lh(en) ? Math.round(en.getBoundingClientRect().height / lh(en)) : 0 };
    })""")
    assert cards, "侧栏应有模板卡"
    for card in cards:
        assert card["h"] <= 170, f"模板卡过高：{card['h']}px（{card}）"
        assert card["zhLines"] <= 2, f"模板名应最多两行，实测 {card['zhLines']} 行"
        assert card["enLines"] <= 2, f"模板描述应最多两行，实测 {card['enLines']} 行"


def test_intake_metrics_have_visual_hierarchy(workbench) -> None:
    """吸收指标此前是一行调试字符串，现在必须是有层级的指标条。"""
    page, _ = workbench
    page.evaluate("window.FoxIntake.open()")
    page.wait_for_timeout(900)
    metrics = page.evaluate("""() => [...document.querySelectorAll('#intake-stats .intake-metric')]
      .map(m => ({ label: m.querySelector('span')?.textContent?.trim() || '',
                   value: m.querySelector('b')?.textContent?.trim() || '',
                   size: parseFloat(getComputedStyle(m.querySelector('b')).fontSize) }))""")
    assert len(metrics) >= 7, f"指标条应有 7 项以上，实测 {len(metrics)}"
    labels = [m["label"] for m in metrics]
    for expected in ("候选", "待审", "已采纳", "组件", "动效", "风格预设"):
        assert expected in labels, f"指标条缺少「{expected}」：{labels}"
    # 数字必须比标签大，否则层级没建立
    for m in metrics:
        assert m["size"] >= 12, f"指标数字应 ≥12px，实测 {m['size']}px（{m['label']}）"


def test_intake_filter_shows_current_selection(workbench) -> None:
    """四个筛选项此前同权重同外观，用户看不出自己在看哪一批。"""
    page, _ = workbench
    page.evaluate("window.FoxIntake.open()")
    page.wait_for_timeout(900)
    state = page.evaluate("""() => [...document.querySelectorAll('[data-intake-filter]')]
      .map(b => ({ f: b.dataset.intakeFilter, pressed: b.getAttribute('aria-pressed'),
                   primary: b.classList.contains('btn-primary') }))""")
    assert len(state) == 4, f"应有四个筛选项，实测 {len(state)}"
    active = [b for b in state if b["pressed"] == "true"]
    assert len(active) == 1, f"必须且只能有一个选中项，实测 {active} / {state}"
    assert active[0]["primary"], "选中项应有主按钮外观"
    # 切换后选中态跟随
    page.evaluate("window.FoxIntake.refresh('approved')")
    page.wait_for_timeout(500)
    now = page.evaluate("""() => [...document.querySelectorAll('[data-intake-filter]')]
      .filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.intakeFilter)""")
    assert now == ["approved"], f"切换后选中态应跟随，实际 {now}"


def test_batch_fetch_is_reachable_in_the_ui(workbench) -> None:
    """S04「多 URL 批量」必须有用户可达路径（曾因 intakeFetchBatch 未定义而整条死掉）。"""
    page, errors = workbench
    page.evaluate("window.FoxIntake.open()")
    page.wait_for_timeout(900)
    assert page.locator("#intake-batch-urls").is_visible() is False, "折叠态默认应收起"
    page.locator(".intake-more summary").click()
    page.wait_for_timeout(400)
    assert page.locator("#intake-batch-urls").is_visible(), "展开后应能看到多 URL 输入"
    page.fill("#intake-batch-urls", "https://example.com/a\nhttps://example.com/b")
    page.click("#intake-batch-btn")
    page.wait_for_function(
        "document.querySelector('#intake-status').textContent.includes('批量抓取')", timeout=10000)
    assert not errors, f"批量抓取触发 JS 错误：{errors}"


def test_modal_backdrop_keeps_context(workbench) -> None:
    """背景模糊此前 12px，把工作台糊成一片，失去「我在哪个界面」的上下文。"""
    page, _ = workbench
    page.evaluate("window.FoxIntake.open()")
    page.wait_for_timeout(700)
    blur = page.evaluate(
        "getComputedStyle(document.querySelector('.preview-modal')||document.body)"
        ".backdropFilter || getComputedStyle(document.querySelector('.preview-modal')||document.body).webkitBackdropFilter")
    px = float(blur.replace("blur(", "").replace("px)", "")) if blur and "px" in blur else 0
    assert 0 < px <= 8, f"背景模糊应 ≤8px 以保留上下文，实测 {blur}"
