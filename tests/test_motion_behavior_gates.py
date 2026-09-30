"""动效的行为门禁：节奏预算、降级偏好、取消与清理。

动效系统（`motion-system.js`）是前端少有的「深 Module」——WAAPI 实现、节奏
token、reduced-motion 降级、可取消、并发上限、可见性处理都关在它的
Interface 后面。本文件从**行为**而不是样式表去验证它：

1. 节奏在预算内（短反馈不该拖沓，长面板不该卡手）
2. 降级偏好真的关掉动效，而不是只改一个变量
3. 取消是干净的——不留活动动画、不留 class
4. 页面隐藏 / 偏好切换会中止在飞的动画
5. 并发有上限，不会因为快速操作堆出一长串动画
"""

from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

READY = "window.FoxMotion && window.FoxWorkbenchUI && nodes.length >= 1"


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
        page.wait_for_timeout(500)
        yield page, errors
        browser.close()


def test_motion_tokens_stay_inside_budget(workbench) -> None:
    """反馈要快、面板要稳：太慢的反馈会被当成卡顿，太快则读不到状态变化。"""
    page, _ = workbench
    tokens = page.evaluate("window.FoxMotion.tokens")
    assert tokens["feedback"] <= 200, f"反馈动效应 ≤200ms，实测 {tokens['feedback']}"
    assert tokens["enter"] <= 260, f"入场动效应 ≤260ms，实测 {tokens['enter']}"
    assert tokens["panel"] <= 320, f"面板动效应 ≤320ms，实测 {tokens['panel']}"
    assert tokens["feedback"] < tokens["enter"] <= tokens["panel"], (
        f"节奏应递增（反馈 < 入场 ≤ 面板），实测 {tokens}")


def test_reduced_motion_actually_disables_animation(workbench) -> None:
    """降级必须是「真的不播」，而不是只改一个没人读的变量。"""
    page, _ = workbench
    assert page.evaluate("window.FoxMotion.setPreference('reduced')") is True
    page.wait_for_timeout(300)
    assert page.evaluate("window.FoxMotion.enabled()") is False
    # play() 在降级下应直接返回空实现，不产生任何活动动画
    after = page.evaluate("""() => {
      const el = document.querySelector('.node');
      window.FoxMotion.play('reveal', el);
      return window.FoxMotion.activeCount;
    }""")
    assert after == 0, f"降级偏好下不应有活动动画，实测 {after}"
    # 关闭档位同样
    page.evaluate("window.FoxMotion.setPreference('off')")
    page.wait_for_timeout(200)
    assert page.evaluate("window.FoxMotion.enabled()") is False
    # CSS 层也要真的关掉
    transition = page.evaluate(
        "getComputedStyle(document.querySelector('.node')).transitionDuration")
    assert transition in ("0s", "0ms"), f"降级下 transition 应为 0，实测 {transition}"


def test_system_preference_restores_playback(workbench) -> None:
    """从「关闭动效」切回「跟随系统」应能恢复播放。"""
    page, _ = workbench
    page.evaluate("window.FoxMotion.setPreference('off')")
    page.wait_for_timeout(200)
    page.evaluate("window.FoxMotion.setPreference('system')")
    page.wait_for_timeout(300)
    assert page.evaluate("window.FoxMotion.enabled()") is True, "跟随系统应恢复播放"
    count = page.evaluate("""() => {
      const el = document.querySelector('.node');
      window.FoxMotion.play('reveal', el);
      return window.FoxMotion.activeCount;
    }""")
    assert count >= 1, "恢复后 play() 应产生活动动画"


def test_cancel_leaves_no_residue(workbench) -> None:
    """取消必须干净：不留活动条目，也不留 animateClass 加上的 class。"""
    page, _ = workbench
    state = page.evaluate("""() => {
      const el = document.querySelector('.node');
      const scope = el.querySelector('.node-head') || el;
      window.FoxMotion.play('reveal', scope, el);
      const during = window.FoxMotion.activeCount;
      window.FoxMotion.animateClass(scope, 'probe-class', 'fox-probe', 4000);
      const withClass = window.FoxMotion.activeCount;
      window.FoxMotion.cancel(el);
      return { during, withClass,
               after: window.FoxMotion.activeCount,
               classLeft: scope.classList.contains('probe-class'),
               animations: document.getAnimations().filter(a => a.playState === 'running').length };
    }""")
    assert state["during"] >= 1, state
    assert state["withClass"] >= 1, state
    assert state["after"] == 0, f"取消后活动条目应清零，实测 {state}"
    assert not state["classLeft"], f"取消后不应残留 class，实测 {state}"
    assert state["animations"] == 0, f"取消后不应有仍在运行的动画，实测 {state}"


def test_visibility_change_cancels_in_flight(workbench) -> None:
    """切到后台应中止在飞的动画，回来时不应有僵尸动画在跑。"""
    page, _ = workbench
    started = page.evaluate("""() => {
      const el = document.querySelector('.node');
      window.FoxMotion.play('panel', el.querySelector('.node-head') || el, el);
      return window.FoxMotion.activeCount;
    }""")
    assert started >= 1, "应先有活动动画"
    page.evaluate("""() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    page.wait_for_timeout(200)
    assert page.evaluate("window.FoxMotion.activeCount") == 0, "页面隐藏后活动动画应被中止"


def test_concurrent_animations_are_capped(workbench) -> None:
    """并发必须有上限：快速操作不应堆出一长串动画拖慢交互。"""
    page, errors = workbench
    count = page.evaluate("""() => {
      const el = document.querySelector('.node');
      const head = el.querySelector('.node-head') || el;
      for (let i = 0; i < 40; i++) {
        window.FoxMotion.play('reveal', head, el.querySelector('.node-body') || head);
      }
      return window.FoxMotion.activeCount;
    }""")
    assert count <= 8, f"并发活动动画应 ≤8，实测 {count}"
    page.evaluate("window.FoxMotion.cancelAll()")
    assert page.evaluate("window.FoxMotion.activeCount") == 0, "cancelAll 应清空"
    assert not errors, f"动效过程中出现 JS 错误：{errors}"
