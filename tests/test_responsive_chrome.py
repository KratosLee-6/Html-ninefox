"""平板与窄屏的顶栏证据门禁：版本徽标可见、进度条不溢出。

两个缺陷都在 v0.7.0 的 README 实拍里被肉眼发现：

  * 768 宽下时间线溢出——五个 `tl-stage` 各有 `min-width:120px` 加标题，
    一行放不下，右缘把「生成产物」截掉一半（horizontal scroll 看起来
    就像布局断了）。修复：≤1100 收成圆点进度条，只保留当前 / 失败
    步骤的文字。
  * 390 宽下 `#ver` 被 `workbench-system.css` 的 ≤420 规则整个
    `display:none`——移动端截图因此无法自证版本。修复：改小字号保留。

这两条是「修 CSS 断言计算样式」的门禁：把修复的规则删掉，测试必须
变红（跑法见 scripts/mutate_responsive_gates.py）。
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.conftest import WorkbenchServer  # noqa: E402


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def workbench_url(tmp_path_factory):
    from htmlninefox.server import app as server_app
    from http.server import ThreadingHTTPServer
    import threading
    import time

    root = tmp_path_factory.mktemp("responsive-chrome")
    server_app._OUTPUT_ROOT = root
    port = _free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), server_app._Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


def _chrome_state(page, selector: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {w: r.width, h: r.height, text: (el.textContent || '').trim(),
                  scrollW: el.scrollWidth, clientW: el.clientWidth};
        }""",
        selector)


def test_timeline_never_overflows_at_tablet_width(workbench_url):
    """768 宽：时间线必须完整可见（v0.7.0 实拍里右缘截断了「生成产物」）。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 768, "height": 1024})
        page.goto(workbench_url + "/", wait_until="networkidle")
        page.wait_for_timeout(1000)
        state = _chrome_state(page, ".timeline")
        browser.close()
    assert state is not None, "找不到 .timeline"
    assert state["scrollW"] <= state["clientW"] + 1, (
        f"768 宽下时间线横向溢出：scroll {state['scrollW']} > client {state['clientW']}——"
        "五个步骤名放不下一行时应收成圆点进度条")


def test_version_badge_stays_visible_on_mobile(workbench_url):
    """390 宽：版本徽标必须可见（移动端截图要能自证版本）。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(workbench_url + "/", wait_until="networkidle")
        page.wait_for_timeout(1000)
        state = _chrome_state(page, "#ver")
        browser.close()
    assert state is not None, "找不到 #ver"
    assert state["w"] > 0 and state["h"] > 0, "#ver 在 390 宽下不可见——" \
        "移动端截图无法自证版本"
    assert state["text"].startswith("v"), f"#ver 内容异常：{state['text']!r}"
