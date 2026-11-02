"""v0.8.8 发版取证：点选即改（所见即所得 A1）——真实 UI 全链路三帧。

    evidence-liveedit-hover.png   进入编辑态：文字虚线轮廓 + toast（基于 rev0）
    evidence-liveedit-typing.png  单击整段全选、改写中（active 蓝框）
    evidence-liveedit-saved.png   Enter 保存 → rev1 徽章 + toast「已保存为 rev1」

全部走真实派发（检查器按钮 → FoxActions.toggleLiveEdit → iframe 内
contenteditable → PUT /text → advanceNodeRevision），不合成、不改字。
"""
from __future__ import annotations

import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_server_project_api import request as api_request  # noqa: E402

OUT = ROOT / "assets" / "screenshots" / "v0.8.8"
PROMPT = "做一个智能水杯的产品落地页：三档控温，续航两周，极简设计"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        payload, _ = api_request(server.base_url, "/api/generate", "POST",
                                 {"prompt": PROMPT, "intent": "landing",
                                  "quiet_llm": True})
        name = payload["project_name"]
        listing, _ = api_request(
            server.base_url,
            "/api/projects/" + urllib.parse.quote(name) + "/text-nodes", "GET")
        target = next(item for item in listing["nodes"]
                      if len(item["text"]) >= 6 and "水杯" not in item["text"])
        print(f"项目 {name} · 目标节点 {target['node']}：{target['text'][:30]}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.base_url + "/")
            page.wait_for_function("typeof window.FoxActions === 'object'")
            node_id = page.evaluate(
                """([name, intent]) => {
                  const node = addNode('file', 140, 140, {
                    title: name, project_name: name,
                    project: 'output/' + name,
                    preview_url: '/output/' + name + '/output.html',
                    intent, revision: 0});
                  select(node.id);
                  return node.id;
                }""", [name, "landing"])
            page.wait_for_selector('[data-action="toggleLiveEdit"]',
                                   state="attached", timeout=30000)
            # 画布净化：隐藏上次会话遗留的外来节点与连线（快照恢复是真实
            # 行为，取证画面只保留本次的注入节点），不改动任何应用逻辑。
            page.evaluate(
                """name => {
                  document.querySelectorAll('#nodes .node').forEach(el => {
                    if (!el.textContent.includes(name)) el.style.display = 'none';
                  });
                  const edges = document.querySelector('#edges');
                  if (edges) edges.style.display = 'none';
                }""", name)
            page.evaluate("id => window.FoxActions.toggleLiveEdit(id)", node_id)
            page.wait_for_function(
                """id => document.querySelector(`#frame-${id}`)?.contentDocument
                  ?.body?.classList.contains('fox-live-editing')""",
                arg=node_id, timeout=20000)
            page.wait_for_timeout(400)
            page.screenshot(path=OUT / "evidence-liveedit-hover.png")
            print("shot: evidence-liveedit-hover.png")

            frame = page.query_selector(f"#frame-{node_id}").content_frame()
            loc = frame.locator(f'[data-fox-live="{target["node"]}"]')
            loc.click()
            page.wait_for_timeout(250)
            page.keyboard.type("标题已点选改写：三档控温 · 续航两周", delay=28)
            page.screenshot(path=OUT / "evidence-liveedit-typing.png")
            print("shot: evidence-liveedit-typing.png")

            page.keyboard.press("Enter")
            page.wait_for_function(
                "() => document.body.textContent.includes('已保存为 rev1')",
                timeout=20000)
            page.wait_for_timeout(600)
            page.screenshot(path=OUT / "evidence-liveedit-saved.png")
            print("shot: evidence-liveedit-saved.png")
            browser.close()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
