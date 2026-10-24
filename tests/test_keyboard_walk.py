"""键盘走查门禁（v0.8.3 键盘可达性专项）。

真浏览器逐个检查两处界面（工作台 + classic）里**可见**的每个 data-action
控件：要么原生可交互（button/a/input…），要么显式 role=button ＋ tabindex，
装饰性遮罩必须标 aria-hidden——三者都不是就是键盘死角。
再用 Tab 键盘焦点验证焦点环没有被拆掉；最后分别在两页真按键盘，断言
动作真的派发了——classic 的五个控件正是被这套走查抓回来的：v0.7.8 的
C6 迁移把它们的内联 onclick 改成了 data-action，但 classic 不加载
fox-core.js，没人消费这些标记，死了一周没人发现。
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright
from test_server_project_api import request as api_request

SWEEP_JS = """
() => {
  const native = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
  return Array.from(document.querySelectorAll('[data-action]')).map(el => {
    const visible = !!(el.offsetParent || el.getClientRects().length)
      && getComputedStyle(el).visibility !== 'hidden';
    return {
      action: el.dataset.action,
      tag: el.tagName,
      native: native.includes(el.tagName),
      role: el.getAttribute('role') || '',
      tabindex: el.tabIndex,
      ariaHidden: el.getAttribute('aria-hidden') === 'true',
      visible,
    };
  });
}
"""


def assert_sweep(items: list[dict], page_name: str) -> None:
    """可见控件三条出路：原生交互 / role=button＋可聚焦 / 显式装饰。"""
    for item in items:
        if not item["visible"]:
            continue
        label = f"{page_name} · {item['tag']}#{item['action']}"
        ok = (
            item["native"]
            or (item["role"] == "button" and item["tabindex"] >= 0)
            or item["ariaHidden"]
        )
        assert ok, (
            f"{label} 不可键盘操作：非原生元素需要 role=button + tabindex，"
            f"或标注 aria-hidden（当前 role={item['role']!r}, "
            f"tabindex={item['tabindex']}, aria-hidden={item['ariaHidden']}）")


def test_every_visible_data_action_is_keyboard_operable(workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for path, name, ready in [
            ("/", "index", "window.FoxDocx && window.FoxIntake"),
            ("/classic", "classic", "typeof generate === 'function'"),
        ]:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(server.base_url + path)
            page.wait_for_function(ready)
            assert_sweep(page.evaluate(SWEEP_JS), name)
            page.close()
        browser.close()


def test_keyboard_focus_keeps_a_visible_ring(workbench_server):
    """Tab 到第一个 data-action 按钮，:focus-visible 的描边不能是 none。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")

        target = page.locator(
            "#tl-actions [data-action], .topbar [data-action], button[data-action]"
        ).first
        target.wait_for(state="visible")
        for _ in range(40):
            page.keyboard.press("Tab")
            if page.evaluate(
                "el => document.activeElement === el", target.element_handle()):
                break
        assert page.evaluate(
            "el => document.activeElement === el", target.element_handle()), \
            "40 次 Tab 都没落到目标按钮——它在 Tab 序外"

        style = page.evaluate("""el => {
            const cs = getComputedStyle(el);
            return { outline: cs.outlineStyle, width: cs.outlineWidth,
                     boxShadow: cs.boxShadow };
        }""", target.element_handle())
        has_ring = (style["outline"] != "none"
                    or (style["boxShadow"] or "none") not in ("none", ""))
        assert has_ring, f"键盘焦点没有可见环：{style}"
        browser.close()


def test_classic_controls_are_alive_again(workbench_server):
    """v0.7.8 C6 迁移后 classic 的按钮死了一周——这条是它们的复活证书。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/classic")
        page.wait_for_function("typeof generate === 'function'")

        # #go 点击真的走了 generate（空需求给出人话提示，不是沉默）
        page.click("#go")
        assert "请先写一句话需求" in page.inner_text("#gen-status"), \
            "生成按钮没有接上 generate()"

        # 等 init 尾部那次 loadProjects() 收尾（#projects 出现内容），
        # 再装探针——否则它和点击派发会撞车，spy 数出 2 次。
        page.wait_for_selector("#projects .tagline, #projects .hist-item")
        url_before = page.url
        page.evaluate("""() => {
            window.__linkSpy = [];
            window.__clickProbe = [];
            document.addEventListener('click', e => window.__clickProbe.push(
                e.target.tagName + ':' + (e.target.closest('[data-action]')?.dataset.action || '-')), true);
            window.loadProjects = () => window.__linkSpy.push(1);
        }""")
        page.click("a[data-action='loadProjects']")
        assert page.evaluate("() => window.__linkSpy.length === 1"), \
            (f"刷新链接没有派发 loadProjects：spy="
             f"{page.evaluate('() => window.__linkSpy.length')}，"
             f"click 事件={page.evaluate('() => window.__clickProbe')}，"
             f"绑定检查={page.evaluate('() => String(typeof window.loadProjects)')}")
        assert page.url == url_before, "href='#' 没有被拦住，页面跳走了"
        browser.close()


def test_classic_history_item_opens_by_enter(workbench_server):
    """classic 历史项是 role=button 的 div——Enter/Space 必须真的派发动作。"""
    with workbench_server as server, sync_playwright() as playwright:
        api_request(server.base_url, "/api/generate", "POST",
                    {"prompt": "键盘走查用的一次性项目", "quiet_llm": True})

        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/classic")
        page.wait_for_selector(".hist-item", timeout=15000)

        # 动作派发的终点换成探针——走查要证的是「Enter 派发了动作」，
        # 不是「openProject 的业务副作用」。
        page.evaluate("""() => {
            window.__kbSpy = [];
            window.openProject = (project, url) => window.__kbSpy.push({project, url});
        }""")
        item = page.locator(".hist-item").first
        item.focus()
        page.keyboard.press("Enter")
        assert page.evaluate(
            "() => window.__kbSpy.length === 1"
            " && String(window.__kbSpy[0].project || '').length > 0"), \
            "Enter 没有派发 openProject"

        # Space 走同一条路（防回归到「只有 Enter 能用」）
        item.focus()
        page.keyboard.press(" ")
        assert page.evaluate("() => window.__kbSpy.length === 2"), \
            "Space 没有派发 openProject"
        browser.close()


def test_workbench_keydown_path_dispatches_non_native_actions(workbench_server):
    """工作台委托层的 keydown 路径（fox-core.js）：非原生元素 Enter 派发。

    工作台存量控件全是原生 button——这条路目前只有通用基础设施在走，
    用一个真实的表内动作（loadProjects）验证派发契约本身。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxDocx && window.FoxIntake")

        page.evaluate("""() => {
            window.__kbSpy = [];
            const table = window.FoxActions;
            table.loadProjects = () => window.__kbSpy.push('loadProjects');
            const probe = document.createElement('div');
            probe.dataset.action = 'loadProjects';
            probe.setAttribute('role', 'button');
            probe.tabIndex = 0;
            probe.textContent = '键盘探针';
            document.body.append(probe);
            probe.focus();
        }""")
        page.keyboard.press("Enter")
        assert page.evaluate("() => window.__kbSpy.length === 1"), \
            "fox-core 的 keydown 路径没有派发非原生动作"
        browser.close()
