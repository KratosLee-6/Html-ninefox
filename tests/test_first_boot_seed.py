"""首启种子必须活过「过早持久化」竞态（真实浏览器 + 真实服务端）。

缺陷（v0.7.7 发布前的全量回归抓到，test_v061_mobile_library 的 READY
超时只是它的症状）：boot 的六个加载器里 alliance 常常最慢，它完成后的
一个同步延续会在**首启种子写入之前**触发一次 save()——此刻画布还是空的，
226 字节的「空工作区」被写进 localStorage，其 650ms 防抖再 PUT 到服务端。
loadSaved/loadRemoteWorkspace 随后把这个空快照当成「已恢复」，种子在本次
与后续每一次启动都被杀掉：用户看到的是空画布，且空态被永久记住。

修复：save() 在 allowNodeEnter（初始化完成标记）之前是 no-op；boot 尾部
显式 save() 一次落盘完整状态。本门禁用 route 延迟把 alliance 钉成最后
完成的加载器，确定性打开竞态窗，断言三件事：

  1. 首次加载：种子存活（nodes ≥ 5），而不是空画布；
  2. 服务端快照：boot 落盘的是 5 节点的完整状态，不是空毒；
  3. 第二次加载：从快照正确恢复，依然 5 节点。
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

READY_TIMEOUT = 20.0
ALLIANCE_DELAY_S = 0.6


def _poll_nodes(page, timeout_s: float) -> int:
    """100ms 显式轮询；wait_for_function 默认 rAF 轮询会被同一缺陷拖死。"""
    deadline = time.monotonic() + timeout_s
    last = -1
    while time.monotonic() < deadline:
        last = page.evaluate("() => nodes.length")
        if last >= 5:
            return last
        time.sleep(0.1)
    return last


def _delay_alliance(page) -> None:
    def handler(route):
        time.sleep(ALLIANCE_DELAY_S)
        try:
            response = page.request.get(route.request.url)
            route.fulfill(response=response)
        except Exception:  # 页面已关闭等场景：放行走真实网络
            try:
                route.continue_()
            except Exception:
                pass

    page.route("**/api/alliance", handler)


def test_first_boot_seed_survives_and_persists(workbench_server):
    pytest.importorskip("playwright")
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        _delay_alliance(page)
        page.add_init_script("try{localStorage.clear()}catch(e){}")

        page.goto(server.base_url + "/")
        nodes = _poll_nodes(page, READY_TIMEOUT)
        assert nodes >= 5, (
            f"首启种子没有存活（nodes={nodes}）——初始化完成前的画布被持久化，"
            f"空快照反过来杀掉了种子。save() 的 allowNodeEnter 守卫被移除了？")

        # 服务端快照必须是完整状态，而不是空毒
        snapshot = None
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            data = page.evaluate(
                "async () => { const r = await fetch('/api/workspace');"
                " return r.json(); }")
            if data.get("exists"):
                snapshot = data
                break
            time.sleep(0.2)
        assert snapshot is not None, "boot 完成后服务端没有工作区快照——boot 尾部的显式 save() 被移除了？"
        remote_nodes = (snapshot.get("state", {}).get("canvas", {})
                        .get("nodes", []))
        assert len(remote_nodes) >= 5, (
            f"服务端快照只有 {len(remote_nodes)} 个节点——空工作区被持久化了"
            f"（过早保存的毒没有除掉）")

        # 第二次加载：从快照恢复，依然是完整工作区
        page2 = browser.new_page(viewport={"width": 390, "height": 844})
        _delay_alliance(page2)
        page2.add_init_script("try{localStorage.clear()}catch(e){}")
        page2.goto(server.base_url + "/")
        nodes2 = _poll_nodes(page2, READY_TIMEOUT)
        assert nodes2 >= 5, (
            f"第二次加载没有从快照恢复（nodes={nodes2}）——空快照污染了后续启动")
        browser.close()
