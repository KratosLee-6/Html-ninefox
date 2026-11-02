"""点选即改门禁（v0.8.8 · 所见即所得 A1）。

A1 把 deck 专属的幻灯片编辑推广到全部意图：GET text-nodes 枚举一切可见
文本（复用 _TextNodeMapper 的字符跨度），PUT text 在项目锁 + 乐观锁下
走同一 apply_text_edits → revisions.commit(kind="text-edit")。

两层防线（v0.7.4 一致性教训）：
  * 前端回传 current（现文），服务端与映射表比对——DOM 枚举与字符跨度
    错位时 409 拒改，绝不改错节点；
  * 浏览器一致性门禁：真实渲染的 landing 里，前端 walker 枚举数与服务器
    映射表必须一一对应（lifecycle-liveedit.js 与本文件用同一套过滤器）。

回归护栏：deck 分组（iter_slide_texts / GET slides）行为不得被
include_orphans 改动。
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="浏览器一致性门禁需要 playwright")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_server_project_api import request as api_request  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


@pytest.fixture()
def workbench(tmp_path: Path):
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def _make(workbench, prompt: str, intent: str) -> str:
    payload, _ = api_request(workbench.base_url, "/api/generate", "POST",
                             {"prompt": prompt, "intent": intent, "quiet_llm": True})
    return payload["project_name"]


def _text_nodes(workbench, name: str) -> dict:
    path = "/api/projects/" + urllib.parse.quote(name) + "/text-nodes"
    payload, _ = api_request(workbench.base_url, path, "GET")
    assert payload["ok"] is True
    return payload


def _edit(workbench, name: str, body: dict, expected: int = 200) -> dict:
    path = "/api/projects/" + urllib.parse.quote(name) + "/text"
    payload, _ = api_request(workbench.base_url, path, "PUT", body, expected=expected)
    return payload


def test_text_nodes_list_landing_texts(workbench):
    name = _make(workbench, "做一个智能水杯的落地页：三档控温，续航两周", "landing")
    listing = _text_nodes(workbench, name)
    assert listing["nodes"], "landing 必须能枚举出可见文本（include_orphans 生效）"
    assert all(item["slide"] == -1 for item in listing["nodes"]), \
        "无 slide 分区的产物，节点应归入孤儿区（slide=-1）"
    assert listing["revision"] == 0
    texts = " ".join(item["text"] for item in listing["nodes"])
    assert "智能水杯" in texts, f"枚举应覆盖标题文案：{texts[:120]}"


def test_text_edit_roundtrip_creates_revision(workbench):
    name = _make(workbench, "做一个智能水杯的落地页：三档控温，续航两周", "landing")
    listing = _text_nodes(workbench, name)
    target = listing["nodes"][0]

    result = _edit(workbench, name, {
        "edits": [{"slide": target["slide"], "node": target["node"],
                   "text": "点选即改的新文案", "current": target["text"]}],
        "expected_revision": listing["revision"],
    })
    assert result["ok"] is True and result["revision"] == listing["revision"] + 1

    html = (workbench.output_root / name / "output.html").read_text(encoding="utf-8")
    assert "点选即改的新文案" in html, "编辑必须写进 output.html"

    after = _text_nodes(workbench, name)
    assert after["nodes"][target["node"]]["text"] == "点选即改的新文案", \
        "同一位点的再枚举必须看到新文本"


def test_text_edit_then_restore_returns_old_text(workbench):
    name = _make(workbench, "做一个智能水杯的落地页：三档控温，续航两周", "landing")
    listing = _text_nodes(workbench, name)
    target = listing["nodes"][0]
    result = _edit(workbench, name, {
        "edits": [{"slide": target["slide"], "node": target["node"],
                   "text": "改过的文案", "current": target["text"]}],
        "expected_revision": listing["revision"],
    })
    restored, _ = api_request(workbench.base_url,
                              "/api/projects/" + urllib.parse.quote(name) + "/restore-revision",
                              "POST", {"revision": listing["revision"],
                                       "expected_revision": result["revision"]})
    assert restored["ok"] is True
    html = (workbench.output_root / name / "output.html").read_text(encoding="utf-8")
    assert "改过的文案" not in html and target["text"] in html, "恢复后旧文必须回来"


def test_text_edit_rejects_stale_revision(workbench):
    name = _make(workbench, "做一个智能水杯的落地页：三档控温", "landing")
    listing = _text_nodes(workbench, name)
    target = listing["nodes"][0]
    error = _edit(workbench, name, {
        "edits": [{"slide": target["slide"], "node": target["node"],
                   "text": "任何", "current": target["text"]}],
        "expected_revision": listing["revision"] + 5,
    }, expected=409)
    assert error["error"]["code"] == "revision_conflict"


def test_text_edit_rejects_mismatched_current(workbench):
    """失配防护：current 与映射表不一致 → 409，且不产生新修订。"""
    name = _make(workbench, "做一个智能水杯的落地页：三档控温", "landing")
    listing = _text_nodes(workbench, name)
    target = listing["nodes"][0]
    error = _edit(workbench, name, {
        "edits": [{"slide": target["slide"], "node": target["node"],
                   "text": "新文案", "current": "这段文字根本不在页面上"}],
        "expected_revision": listing["revision"],
    }, expected=409)
    assert error["error"]["code"] == "text_node_mismatch"
    assert _text_nodes(workbench, name)["revision"] == listing["revision"], \
        "失配拒绝不得留下新修订"


def test_text_edit_rejects_out_of_range_node(workbench):
    name = _make(workbench, "做一个智能水杯的落地页：三档控温", "landing")
    listing = _text_nodes(workbench, name)
    error = _edit(workbench, name, {
        "edits": [{"slide": -1, "node": len(listing["nodes"]) + 99,
                   "text": "越界", "current": "x"}],
        "expected_revision": listing["revision"],
    }, expected=409)
    assert error["error"]["code"] == "text_edit_noop"


def test_text_edit_requires_edits(workbench):
    name = _make(workbench, "做一个智能水杯的落地页", "landing")
    error = _edit(workbench, name, {"edits": [], "expected_revision": 0}, expected=400)
    assert error["error"]["code"] == "text_edit_empty"


def test_deck_grouping_survives_include_orphans(workbench):
    """回归护栏：include_orphans 不得改变 deck 幻灯片清单的行为。"""
    name = _make(workbench, "做一个新品发布会演示：主题演讲，三页议程", "deck")
    path = "/api/projects/" + urllib.parse.quote(name)
    slides, _ = api_request(workbench.base_url, path + "/slides", "GET")
    assert slides["slides"], "deck 的幻灯片清单必须照常工作"
    assert all(group["index"] >= 0 for group in slides["slides"]), \
        "幻灯片清单仍按分区归类（不含孤儿节点）"
    listing = _text_nodes(workbench, name)
    slides_nodes = [item["node"] for group in slides["slides"]
                    for item in group["texts"]]
    orphan_nodes = [item["node"] for item in listing["nodes"] if item["slide"] == -1]
    # deck 模板目前整页都在 section 内（0 孤儿是真实形态）；landing 侧已
    # 覆盖孤儿路径，这里守住「分组与点选枚举同源且互斥」。
    assert not (set(slides_nodes) & set(orphan_nodes)), \
        "同一字符跨度不得同时出现在分区与孤儿区"
    # 同一 HTML 两套枚举共享稳定 node id：分区内的 node 在全序列里也存在
    all_nodes = {item["node"] for item in listing["nodes"]}
    assert set(slides_nodes) <= all_nodes, "幻灯片清单编号必须与点选枚举同源"


def test_frontend_walker_matches_server_mapping(workbench):
    """一致性门禁（v0.7.4 教训）：真实渲染的 landing 里，前端 walker
    （与 lifecycle-liveedit.js 同一套过滤器）枚举的文本节点必须与服务器
    映射表逐位对应——数目一致且抽样文本相等。"""
    name = _make(workbench, "做一个智能水杯的落地页：三档控温，续航两周", "landing")
    listing = _text_nodes(workbench, name)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(workbench.base_url + f"/output/{urllib.parse.quote(name)}/output.html")
        page.wait_for_timeout(1500)   # 墨水落纸 / 显形动效放完，内容到终态
        sampled = page.evaluate(
            """() => {
              const walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, {
                  acceptNode(node) {
                    const tag = node.parentElement?.tagName?.toLowerCase();
                    if (tag === 'script' || tag === 'style') return NodeFilter.FILTER_REJECT;
                    if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                  },
                });
              const out = [];
              for (let n = walker.nextNode(); n; n = walker.nextNode()) {
                out.push(n.nodeValue.replace(/\\s+/g, ' ').trim());
              }
              return out;
            }""")
        browser.close()
    assert len(sampled) == len(listing["nodes"]), (
        f"前端 walker {len(sampled)} ≠ 服务器映射 {len(listing['nodes'])}——"
        "点选即改会改错节点，两端过滤器必须一致")
    server_texts = [item["text"] for item in listing["nodes"]]
    for index in range(0, len(sampled), max(1, len(sampled) // 5)):
        assert sampled[index] == server_texts[index], (
            f"节点 {index} 文本失位：{sampled[index]!r} ≠ {server_texts[index]!r}")


def test_click_to_edit_ui_roundtrip(workbench):
    """端到端冒烟：检查器按钮进编辑态 → iframe 内点字即改 → 保存出 rev+1。
    走真实派发路径（FoxActions.toggleLiveEdit），画布节点按已知做法注入。"""
    name = _make(workbench, "做一个智能水杯的落地页：三档控温，续航两周", "landing")
    listing = _text_nodes(workbench, name)
    target = next(item for item in listing["nodes"] if len(item["text"]) >= 4)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(workbench.base_url + "/")
        page.wait_for_function("typeof window.FoxActions === 'object'")
        node_id = page.evaluate(
            """([name, intent]) => {
              const node = addNode('file', 120, 120, {
                title: name, project_name: name,
                project: 'output/' + name,
                preview_url: '/output/' + name + '/output.html',
                intent, revision: 0});
              select(node.id);
              return node.id;
            }""", [name, "landing"])
        # 按钮必须在场（接线由注册表 + 死按钮门禁双护）；检查器存在重渲染
        # 竞态，page.click 不稳——直接走 FoxActions 派发，与按钮 onclick
        # 是同一个函数。
        page.wait_for_selector('[data-action="toggleLiveEdit"]', timeout=30000,
                               state="attached")
        page.evaluate("id => window.FoxActions.toggleLiveEdit(id)", node_id)
        page.wait_for_function(
            """id => {
              const f = document.querySelector(`#frame-${id}`);
              return Boolean(f?.contentDocument?.body
                ?.classList.contains('fox-live-editing'));
            }""", arg=node_id, timeout=20000)
        frame_el = page.query_selector(f"#frame-{node_id}")
        frame = frame_el.content_frame()
        frame.locator(f'[data-fox-live="{target["node"]}"]').click()
        page.keyboard.insert_text("点选改写的新标题")
        page.keyboard.press("Enter")
        # 保存成功 → 工作区 toast 提到新 rev
        page.wait_for_function(
            """() => document.body.textContent.includes('已保存为 rev1')""",
            timeout=20000)
        browser.close()
    assert not errors, f"页面错误：{errors}"

    html = (workbench.output_root / name / "output.html").read_text(encoding="utf-8")
    assert "点选改写的新标题" in html, "UI 编辑必须经 PUT /text 落盘"
    after = _text_nodes(workbench, name)
    assert after["revision"] == 1 and \
        after["nodes"][target["node"]]["text"] == "点选改写的新标题"
