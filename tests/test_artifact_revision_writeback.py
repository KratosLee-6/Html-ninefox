"""C2：Artifact 前进到新 Revision 的写回协议必须只有一个拥有者。

背景：这段协议此前被复制在 sendFeedback / slides.save / generation.rerun
三处且互不一致——其中 sendFeedback 与 slides.save 都漏了 Workspace 持久化，
于是内存里的 revision 号变了、持久化快照没变。用户刷新页面后看到旧 rev 号，
而服务端 Artifact 已经是新 rev。这正是 v0.6.0 刚对外宣称的核心能力（成果 G4）
在真实使用中会失真的路径。

现在协议收在 `window.FoxRevisions.advanceNodeRevision()` 里。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"
READY = "window.FoxWorkbenchUI && window.FoxRevisions && nodes.length >= 1"


@pytest.fixture
def workbench(tmp_path):
    from tests.conftest import WorkbenchServer

    with WorkbenchServer(tmp_path) as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # 刻意不在 add_init_script 里清 localStorage：init script 会在**每次**
        # 导航（含 reload）时执行，而本用例测的正是 localStorage 里的画布
        # 快照——清了它就等于把被测对象擦掉，用例会永远通过。
        # workbench_server 每次用随机端口，origin 不同，localStorage 天然隔离。
        page.goto(server.base_url + "/")
        page.wait_for_function(READY, timeout=20000)
        page.wait_for_timeout(600)
        yield page, errors
        browser.close()


def test_advance_node_revision_is_the_single_owner() -> None:
    """协议只能存在一份实现：调用点不得再各自拼装写回步骤。"""
    for name in ("lifecycle-revisions.js", "lifecycle-slides.js", "lifecycle-generation.js"):
        source = (STATIC / name).read_text(encoding="utf-8")
        body = source.split("window.Fox", 1)[-1] if "window.Fox" in source else source
        # 徽标 / iframe 破缓存的组合是协议的指纹；除了拥有者本人，
        # 任何调用点再拼一次就说明协议又被复制了。
        if "rev-${" in body and "frame-${" in body:
            pytest.fail(f"{name} 仍在自行拼装 revision 写回协议，应调用 "
                        f"window.FoxRevisions.advanceNodeRevision()")
    owner = (STATIC / "lifecycle-revisions.js").read_text(encoding="utf-8")
    assert "async function advanceNodeRevision(" in owner, "写回协议缺少拥有者"
    assert "persistWorkspaceNow" in owner, "拥有者必须负责持久化 Workspace 快照"


def test_slide_edit_survives_a_page_reload(workbench) -> None:
    """核心回归：幻灯片保存后刷新页面，revision 号不得回退。

    这正是修复前的用户可见缺陷——slides.save 改了内存里的 revision
    却没有持久化，刷新后回到旧 rev。
    """
    page, errors = workbench
    result = page.evaluate(
        """() => {
            const ws = activeWorkspace();
            const req = membersOf(ws).find(n => n.kind === 'requirement');
            // 必须是 deck：落地页没有 <section class="slide">，/slides 读不到分页。
            req.data.text = '做一个极简的发布会 PPT，介绍本地优先的 HTML 工作台';
            return { ws: ws.id, req: req.id };
        }""")
    page.evaluate("id => void advanceWs(id)", result["ws"])
    page.wait_for_selector(".node.output", timeout=60000)
    page.wait_for_function(
        "FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")
    page.wait_for_function("Boolean(document.querySelector('.node.output'))")

    deck = page.evaluate("""() => {
        const n = document.querySelector('.node.output');
        const id = Number(n.id.replace('node-', ''));
        return { id, project: nodes.find(x => x.id === id).data.project_name };
    }""")
    assert deck["project"], "产物应带 project_name，否则无法进入幻灯片编辑"

    # 直接驱动服务端 slides 接口写一个新 Revision，再走拥有者写回界面。
    new_revision = page.evaluate(
        """async ({ id, project }) => {
            const base = '/api/projects/' + encodeURIComponent(project);
            const slides = await (await fetch(base + '/slides')).json();
            const first = slides.slides[0];
            const target = first.texts[0];
            const result = await (await fetch(base + '/slides', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    edits: [{ slide: 0, node: target.node, text: '刷新后仍应保留的标题' }],
                    expected_revision: slides.revision,
                }),
            })).json();
            await window.FoxRevisions.advanceNodeRevision(id, result.revision);
            return result.revision;
        }""", deck)
    assert new_revision >= 1, f"应产生新 Revision，实际 {new_revision}"

    page.wait_for_function(
        "rev => { const n = nodes.find(x => x.id === %d); return n && n.data.revision === rev; }" % deck["id"],
        arg=new_revision)

    # 关键一步：刷新后 revision 号必须仍在，不能退回 0。
    page.reload()
    page.wait_for_function(READY, timeout=20000)
    page.wait_for_timeout(800)
    persisted = page.evaluate(
        "id => { const n = nodes.find(x => x.id === id); return n ? n.data.revision : null; }",
        deck["id"])
    assert persisted == new_revision, (
        f"刷新后 revision 回退：期望 {new_revision}，实际 {persisted}"
        f"（写回没有持久化 Workspace 快照）")
    assert not errors, f"页面出现 JS 错误：{errors}"
