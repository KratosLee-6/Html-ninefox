"""C6 委托运行时的真点击验证（真实浏览器 + 真实启动的工作台）。

静态门禁锁不住的三件事，都在这里用真实点击证明：

  1. **类型契约**——`data-id="3"` 读出来是字符串，签名表必须把它变成
     number 再进动作（`===` 比较 node.id 才不会失效）。间谍替换
     FoxActions.focusWorkspace，真点工作区芯片，断言收到的 id 是 number
     且等值；spy 整体替换动作，不产生真实副作用。
  2. **closest 语义**——点芯片的 ••• 编辑钮必须只触发 editWorkspace、
     不触发芯片自身的 focusWorkspace（旧内联 onclick + stopPropagation
     的等价性，迁移正确性的核心）。
  3. **未知动作必须报错可见**——data-action 指向未登记的名字时委托层
     console.error（死按钮在开发期暴露），而不是静默吞掉。

  无参动作（zoomIn）顺带验证真实行为：点击后相机缩放系数真的变了。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright  # noqa: E402


def _poll(page, expr: str, timeout_s: float = 20.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            value = page.evaluate(f"() => Boolean({expr})")
            if value:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


READY = ("window.FoxInteraction && window.FoxActions && nodes.length >= 5")


def test_delegated_clicks_carry_the_declared_types(workbench_server):
    pytest.importorskip("playwright")
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text)
                if m.type == "error" else None)
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        assert _poll(page, READY), (
            f"工作台未就绪（nodes={page.evaluate('() => nodes.length')}）")

        # 1. 数字参数：真点工作区芯片，focusWorkspace 收到的必须是 number
        page.evaluate("""
          () => {
            window.__spy = [];
            window.FoxActions.focusWorkspace =
              id => window.__spy.push(['focusWorkspace', typeof id, id]);
          }
        """)
        chip = page.locator(".workspace-nav-main").first
        chip.click()
        spy = page.evaluate("() => window.__spy")
        assert spy == [[ "focusWorkspace", "number", spy[0][2] ]] and \
            isinstance(spy[0][2], (int, float)) and spy[0][2] >= 1, (
            f"focusWorkspace 收到的参数不符合签名（{spy}）——"
            f"data-id 字符串没有按签名转成 number，=== 比较将失效")

        # 2. closest 语义：芯片的 ••• 编辑钮只触发 editWorkspace、
        #    不触发芯片自身的 focusWorkspace。注意 ••• 的动作经内联
        #    onpointerdown 触发（指针层绑定，C6 保留），因此替换全局
        #    editWorkspace 才能拦到它；focusWorkspace 则只能经委托层
        #    （替换派发表条目）。断言两者互不越界。
        page.evaluate("""
          () => {
            window.__spy = [];
            window.FoxActions.focusWorkspace =
              id => window.__spy.push('focusWorkspace');
            window.editWorkspace =
              id => window.__spy.push(['editWorkspace', typeof id, id]);
          }
        """)
        page.locator(".workspace-nav-edit").first.click()
        spy = page.evaluate("() => window.__spy")
        assert spy and all(call == "editWorkspace" for call in
                           [entry if isinstance(entry, str) else entry[0]
                            for entry in spy]), (
            f"芯片动作边界被破坏：点击 ••• 触发了 {spy}——外层 focusWorkspace "
            f"不得被触发（旧 stopPropagation 的等价性）。editWorkspace 出现两次"
            f"（内联 pointerdown + 委托 click）与旧内联 onclick 的双重触发一致")
        assert any(isinstance(entry, list) and entry[1] == "number" for entry in spy), (
            f"editWorkspace 收到的 id 不是 number：{spy}")

        # 3. 无参动作的真实行为：点 zoomIn，相机真的放大
        before = page.evaluate("() => camera.z")
        page.locator('[data-action="zoomIn"]').first.click()
        after = page.evaluate("() => camera.z")
        assert after > before, f"zoomIn 点击后相机未变化（{before} -> {after}）"

        # 4. 未知动作：委托层必须 console.error（死按钮在开发期暴露）
        page.evaluate("""
          () => {
            const b = document.createElement('button');
            b.dataset.action = '__no_such_action__';
            b.id = 'delegation-probe';
            document.body.appendChild(b);
          }
        """)
        console_errors.clear()
        page.evaluate("""() => {
          document.getElementById('delegation-probe')
            .dispatchEvent(new MouseEvent('click', {bubbles: true}));
        }""")
        time.sleep(0.3)
        assert any("未登记" in e for e in console_errors), (
            f"未知动作没有触发可见报错（console={console_errors[:3]}）——"
            f"死按钮会静默失败，回到 intakeFetchBatch 事故的形态")

        browser.close()


def test_delegated_string_and_nullable_args(workbench_server):
    pytest.importorskip("playwright")
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        assert _poll(page, READY), "工作台未就绪"

        # 字符串参数：移动端抽屉开关，panel 必须是 'sidebar' 原文
        page.evaluate("""
          () => {
            window.__spy = [];
            window.FoxActions.toggleMobilePanel =
              panel => window.__spy.push(['toggleMobilePanel', typeof panel, panel]);
          }
        """)
        page.locator('[data-action="toggleMobilePanel"][data-panel="sidebar"]').click()
        spy = page.evaluate("() => window.__spy")
        assert spy == [["toggleMobilePanel", "string", "sidebar"]], (
            f"字符串参数失真：{spy}")

        # 可空数字参数：advanceWs 签名 number?——数据属性缺省时收到 null
        page.evaluate("""
          () => {
            window.__spy = [];
            window.FoxActions.advanceWs =
              (id, options) => window.__spy.push(['advanceWs', id === null ? 'null' : typeof id, id]);
          }
        """)
        page.evaluate("""
          () => {
            const b = document.createElement('button');
            b.dataset.action = 'advanceWs';
            b.id = 'nullable-probe';
            b.style.cssText = 'position:fixed;top:0;left:0;width:40px;height:40px;z-index:99999';
            document.body.appendChild(b);
            b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
          }
        """)
        spy = page.evaluate("() => window.__spy")
        assert spy == [["advanceWs", "null", None]], (
            f"number? 契约失真：{spy}——缺省 data-id 必须归 null（advanceWs "
            f"以 null 判定「未归属工作区」），NaN 或 0 都是错")
        browser.close()
