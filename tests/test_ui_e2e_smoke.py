"""UI 行为级冒烟门禁：点下去 → 后端真的做了什么 → 产物真的落盘。

为什么还需要这个文件
--------------------
这个仓库已经发生过两次「所有门禁全绿、功能不能用」的事故，形状完全一样：

* **v0.6.0**：Windows 便携包通过四个构建 job、全部测试通过，**一启动就崩**；
  同一版还有「PPTX 选项缺失」——功能在服务器端看不出任何异常，只在浏览器里缺席。
* **v0.6.2**：SSRF 修复带着三处阻断缺陷发布，**每一次出站抓取都抛 TypeError**，
  而 CI 五个 job 全绿、39 个发布附件逐个下载重算 SHA-256 全过。
* **v0.6.1**：幻灯片竞态，同样只活在浏览器里。

已补上的洞（不重做）：`tests/test_smoke_success_paths.py` + `scripts/mutate_smoke_gates.py`
覆盖后端与产物层；`tests/test_frontend_kernel_loadable.py` +
`scripts/mutate_frontend_kernel_gates.py` 覆盖前端脚本的**加载级与可达级**。

**没覆盖的正是这里：UI 行为级。** `e2e_verify.py` 的 22 条验证的是「能拖动、能翻页、
能渲染出节点」，不是「点了会真的触发后端动作」。前端少登记一个派发表条目、onclick 指向
不存在的函数、导出 payload 少一个字段、生成完成后产物没落盘、某次交互抛了未捕获异常——
这五类故障在已��的每一层门禁下都是全绿的，只有一条真的点下去的门禁会红。

本文件的自我约束
----------------
1. **只断言真实产物**：磁盘上的文件字节、真实 HTTP 响应体、真实 DOM 状态。
   没有任何一条断言是 `assert "某段文本" in read_text()` 那种扫描源码的写法——
   一行注释就能满足，无害重构还会误报（见 `docs/REJECTED-test_gate_quality_gates.py.txt`）。
2. **不 skip、不 xfail**：playwright 是 `pyproject.toml` 的核心依赖，缺 Chromium 就该红。
   观测不到目标时失败，因为 skip 会被读成通过。
3. **每条门禁都被变异验证**：见 `scripts/mutate_ui_gates.py`。「N 条全过」不是证据，
   「在坏代码上会红」才是。
"""

from __future__ import annotations

import json
import sys
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 控制台不支持时不影响断言
    pass

from htmlninefox import pipeline  # noqa: E402

# 与 tests/test_v061_visual_evidence_states.py 同一个就绪判据：不是「页面加载完」，
# 而是「内核 + 五个生命周期模块都挂上了，并且画布已经有种子节点」。
READY = ("window.FoxInteraction && window.FoxCanvasProductivity && window.FoxWorkbenchUI"
         " && window.FoxProjects && window.FoxGeneration && window.FoxRevisions"
         " && window.FoxExports && window.FoxSlides && nodes.length >= 5")

VIEWPORT = {"width": 1440, "height": 900}

# 生成用的真实需求。断言会检查它是否真的出现在落盘的 HTML 里——
# 这是「跑过了」和「渲染了一个空壳模板」的区别。
BRIEF = "做一个能放进行程图的极简作品集站点，重点讲本地优先与离线可用"
BRIEF_KEYWORD = "能放进行程图的极简作品集站点"

# 批量抓取用的私网地址：产品一定拒绝它们，但**必须真的把每个 URL 送到服务端处理**。
# 私网地址正是 SSRF 门禁要拦的东西，用它可以在离线 CI 里得到一份确定的服务端裁决。
BATCH_URLS = ("http://127.0.0.1/\nhttp://10.0.0.1/")


# ------------------------------------------------------------------ 公共工具


def _open_workbench(page: Page, base_url: str, *, clear_storage: bool = True) -> list[str]:
    """打开工作台并收集**未捕获的页面 JS 错误**。

    返回的是活的列表：调用者在整个旅程结束时读它。`page.on("pageerror")` 只捕获
    未捕获异常——v0.6.1 的幻灯片竞态正是这一类，只看 HTTP 状态码看不见它。
    """
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    if clear_storage:
        # 每次导航都清：重载后的画布只能来自服务端快照或磁盘产物，不能来自浏览器缓存。
        page.add_init_script("try{localStorage.clear()}catch(e){}")
    page.goto(base_url + "/")
    page.wait_for_function(READY, timeout=60000)
    return errors


def _add_output_node(page: Page, work: Path, intent: str) -> str:
    """在画布上放一个指向磁盘上真实产物的产物节点（与既有 UI 测试同一手法）。"""
    return page.evaluate(
        """data => {
            const ws = activeWorkspace();
            const node = addNode('output', ws.x + ws.w + 80, ws.y + 30, {
                workspaceId: ws.id, title: data.title, project_name: data.name,
                project: data.name, preview_url: '/output/' + data.name + '/output.html',
                intent: data.intent, preset_id: 'fox-pixel-garden',
                revision: 0, feedback: [],
            });
            select(node.id);
            return node.id;
        }""",
        {"name": work.name, "intent": intent, "title": "产物 · " + intent})


def _assert_no_page_error(page: Page, errors: list[str], where: str) -> None:
    """点击之后立刻断言没有未捕获的页面错误。

    这是本文件最重要的一条纪律。死接线（onclick 指向不存在的名字、导出请求
    payload 被清空、派发表条目被删）抛出的都是**当场**的 ReferenceError 或
    TypeError。而它造成的后果——产物没出现——要等长超时才发现。所以先看错误，
    再看后果。

    那 400ms 不是随便加的 sleep：`pageerror` 由浏览器异步投递回 Python，
    click() 返回时事件可能还在路上。不给一拍，这条断言会漏报真正的死接线，
    然后测试继续去等那个永远不会出现的产物——又变回挂三分钟。
    400ms 足够投递，且在每个变异上只花 0.4 秒。
    """
    page.wait_for_timeout(400)
    if errors:
        raise AssertionError(f"{where}立刻抛出未捕获的页面错误：{errors}")


def _generate_through_the_ui(page: Page, errors: list[str]) -> str:
    """输入需求 → AI 分析 → 采用推荐并生成。返回产物节点 id。

    三步都是真的点击：没有一处 `page.evaluate` 代替用户动作，因为本文件要守的正是
    「onclick 接线」这一层。

    `errors` 是活的页面错误列表。每一次「点了但什么都不会发生」的死接线，都在点击
    那一刻抛 ReferenceError——所以每次点击后**先**断言它为空，再去等后果。
    顺序反过来的话，最后那句等产物的长等待会在每个死接线变异上白等三分钟：
    结果同样是红，但 CI 上表现为 job 超时，而不是「门禁抓到了缺陷」。
    """
    page.get_by_role("button", name="输入需求").click()
    page.wait_for_selector("#create-modal:not([hidden])", timeout=15000)
    page.fill("#creation-prompt", BRIEF)
    page.click("#creation-analyze")
    _assert_no_page_error(page, errors, "点「AI 分析」")
    page.wait_for_selector("text=采用推荐并生成", timeout=45000)
    page.get_by_role("button", name="采用推荐并生成").click()
    _assert_no_page_error(page, errors, "点「采用推荐并生成」")
    page.wait_for_selector(".node.output", timeout=60000)
    return page.evaluate("nodes.find(node => node.kind === 'output').id")


def _assert_a_real_artifact(root: Path, name: str) -> Path:
    """断言产物在磁盘上，而且不是一个占位文件。返回项目目录。"""
    project = root / name
    assert project.is_dir(), f"产物目录没有落盘：{project}"
    artifact = project / "output.html"
    assert artifact.is_file(), f"output.html 没有落盘：{artifact}"
    html = artifact.read_text(encoding="utf-8")
    assert len(html.encode("utf-8")) > 3000, f"产物过小（{len(html.encode())} 字节），可能是空壳"
    assert html.lstrip().lower().startswith("<!doctype html>"), "产物不是完整 HTML 文档"
    assert BRIEF_KEYWORD in html, "产物里没有这次需求的文案——渲染了一个与需求无关的模板"
    assert "--fox-primary" in html, "产物里没有令牌驱动的样式"
    return project


# ------------------------------------------------------------------ 01 生成落盘


def test_ui_generate_click_lands_a_real_artifact_and_a_readable_preview(workbench_server) -> None:
    """点「采用推荐并生成」→ 磁盘上真的有产物，节点预览真的渲染的是它。

    断言的产物：`output_root/<项目>/output.html` 的字节内容（完整文档、含本次需求文案）、
    `.foxstate.json` 的 revision=0、revisions 目录；以及节点预览 iframe 里渲染出的
    h1 与磁盘文件里的 h1 **逐字相同**——「预览框里有个东西」是蒙的，「预览框里就是
    磁盘上那个文件」不是。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        node_id = _generate_through_the_ui(page, errors)
        name = page.evaluate(
            "id => nodes.find(node => node.id === id).data.project_name", node_id)
        assert name, "产物节点上没有项目名"

        project = _assert_a_real_artifact(server.output_root, name)
        state = json.loads((project / pipeline.STATE_FILE).read_text(encoding="utf-8"))
        assert state["revision"] == 0, f"首次生成的 revision 应为 0，实际 {state['revision']}"
        assert (project / "revisions").is_dir(), "产物没有版本目录，版本历史无从谈起"

        heading = page.evaluate(
            """id => {
                const frame = document.getElementById('frame-' + id);
                const doc = frame && frame.contentDocument;
                const node = doc && doc.querySelector('h1, h2');
                return node ? node.textContent.trim() : '';
            }""", node_id)
        assert heading, "产物节点的预览框没有渲染出任何标题"
        on_disk = (project / "output.html").read_text(encoding="utf-8")
        assert heading in on_disk, (
            f"预览框里的标题 {heading!r} 在磁盘产物里找不到——预览的不是刚生成的那个文件")

        assert errors == [], f"生成过程中出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# ------------------------------------------------------------ 02 项目列表 + 重载


def test_ui_project_is_listed_and_survives_a_page_reload(workbench_server) -> None:
    """新建项目 → 出现在素材库「文件」标签 → **重新加载页面后仍在**。

    断言的产物：素材库里的 `data-pid="<项目名>"` 卡片（真实 DOM 状态，名字由
    `/api/projects` 读盘而来）、卡片预览 iframe 里渲染出的正文，以及重载后同样的两件事。
    初始化脚本每次导航都清空 localStorage，所以「重载后仍在」只可能来自磁盘上的产物，
    不可能来自浏览器里残留的画布快照。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        _generate_through_the_ui(page, errors)
        name = page.evaluate("nodes.find(node => node.kind === 'output').data.project_name")
        _assert_a_real_artifact(server.output_root, name)

        def assert_listed() -> str:
            page.click('.tab[data-tab="files"]')
            page.wait_for_selector(f'#pal .pal-card[data-pid="{name}"]', timeout=20000)
            page.wait_for_function(
                """() => {
                    const frame = document.querySelector('#pal .file-thumb iframe');
                    const doc = frame && frame.contentDocument;
                    return !!(doc && doc.body && doc.body.textContent.trim().length > 50);
                }""", timeout=30000)
            return page.evaluate(
                """() => {
                    const doc = document.querySelector('#pal .file-thumb iframe').contentDocument;
                    return doc.querySelector('h1, h2').textContent.trim();
                }""")

        first = assert_listed()
        assert BRIEF_KEYWORD in first, f"项目列表的预览渲染的不是这个产物：{first!r}"

        page.reload()
        page.wait_for_function(READY, timeout=60000)
        after_reload = assert_listed()
        assert after_reload == first, (
            f"重载后列表里渲染的内容变了：{first!r} -> {after_reload!r}")

        assert errors == [], f"项目列表交互中出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# ------------------------------------------------------- 03 HUD 推进按钮这条接线


def test_ui_advance_button_really_drives_the_backend(workbench_server) -> None:
    """点顶部「推进当前工作区」→ 后端真的生成了，产物真的在磁盘上。

    这条专门守 `onclick="advanceActive()"` 这条接线。S20 期间的 `intakeFetchBatch`
    死按钮就是同一形状：HTML 里引用了名字，派发表里没有登记，服务器端与所有单测全绿，
    只有用户点下去才发现按钮什么都不干。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        # 走「先进入工作区自定义」：建一个需求节点，不立刻生成。
        page.get_by_role("button", name="输入需求").click()
        page.wait_for_selector("#create-modal:not([hidden])", timeout=15000)
        page.fill("#creation-prompt", BRIEF)
        page.get_by_role("button", name="先进入工作区自定义").click()
        # 注意 state="hidden"：wait_for_selector 默认等的是「可见」，而这里要等的
        # 恰恰是「弹窗已经不可见」。写成 `#create-modal[hidden]` 会永远等不到。
        page.wait_for_selector("#create-modal", state="hidden", timeout=15000)
        assert page.evaluate(
            "activeWorkspace().id && membersOf(activeWorkspace()).some(n => n.kind === 'requirement')"
        ), "需求没有进入工作区，推进按钮无从谈起"

        # 点下去之后**先**断言没报错，再去等产物。
        #
        # 顺序很重要。死按钮（onclick 指向一个不存在的名字）当场抛 ReferenceError，
        # `pageerror` 一秒内就能看到；而产物永远不会出现，所以
        # wait_for_selector 会一直等到它的超时。两种写法最后都是红，但
        # 「等产物」那条在每个这样的变异上要多花三分钟——五个变异就是
        # 十五分钟纯等待，在 CI 上表现为 job 超时，而不是「门禁抓到了缺陷」。
        # 先断言负向信号，死按钮在一秒内变红；长等待只留给真正会成功的路径。
        page.click("#btn-go")
        page.wait_for_timeout(1500)
        assert errors == [], (
            "点「推进当前工作区」立刻抛出未捕获的页面错误——这正是死按钮的形状："
            f"{errors}")

        # 产物确实出现了，才算这条接线真的通到后端
        page.wait_for_selector(".node.output", timeout=60000)

        name = page.evaluate("nodes.find(node => node.kind === 'output').data.project_name")
        _assert_a_real_artifact(server.output_root, name)
        assert errors == [], f"点推进按钮出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# ------------------------------------------------------------------ 04 PPTX 导出


def test_ui_deck_export_writes_a_real_pptx_archive(workbench_server) -> None:
    """deck 产物在导出中心选 PPTX → 磁盘上真的多了一个**合法 zip**。

    断言的产物：`<项目>/exports/<id>/*.pptx`（能当 zip 打开、有 `[Content_Types].xml`、
    至少 3 张幻灯片、大小合理）、同目录的 `export-report.json`（含幻灯片数），
    以及 UI 上那个「下载」链接按下去返回的**真实响应体**以 `PK` 开头。
    只断言「出现了一个 .pptx 文件」是不够的——v0.6.0 的形状正是「文件在、内容不能用」。
    """
    with workbench_server as server, sync_playwright() as playwright:
        work = pipeline.run_expert(
            "做一个用于导出演示的发布会 PPT", intent_override="deck",
            output=str(server.output_root), quiet_llm=True)["work"]
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        node_id = _add_output_node(page, work, "deck")
        page.get_by_role("button", name="导出 PDF / PNG").click()
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'",
            timeout=60000)
        page.select_option("#export-format", "pptx")
        assert page.locator("#export-start").is_enabled()
        page.click("#export-start")
        # 先看错误再看后果：导出接线断掉时是当场抛错，而不是「两分钟后没有文件」。
        _assert_no_page_error(page, errors, "点「开始导出」")
        page.wait_for_function(
            "document.querySelector('#export-status').textContent.startsWith('导出完成')",
            timeout=60000)

        decks = sorted(work.rglob("*.pptx"))
        assert len(decks) == 1, f"导出后应恰好有一个 pptx，实际 {[p.name for p in decks]}"
        target = decks[0]
        size = target.stat().st_size
        assert size > 10000, f"pptx 过小（{size} 字节），可能是空壳"
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None, "pptx 不是完整可读的 zip"
            names = archive.namelist()
            assert "[Content_Types].xml" in names, "pptx 缺少 [Content_Types].xml，不是合法 OOXML"
            slides = [item for item in names
                      if item.startswith("ppt/slides/slide") and item.endswith(".xml")]
            assert len(slides) >= 3, f"pptx 里只有 {len(slides)} 张幻灯片"

        report = json.loads((target.parent / "export-report.json").read_text(encoding="utf-8"))
        assert report["pptx"]["slides"] == len(slides), "导出报告里的幻灯片数与文件里的对不上"

        hrefs = page.evaluate(
            "() => [...document.querySelectorAll('#export-result a')].map(a => a.getAttribute('href'))")
        pptx_href = next((item for item in hrefs if item and item.endswith('.pptx?download=1')), None)
        assert pptx_href, f"导出结果里没有 pptx 下载链接：{hrefs}"
        with urllib.request.urlopen(server.base_url + pptx_href, timeout=30) as response:
            assert response.status == 200
            assert response.headers.get_content_type() in (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/octet-stream")
            body = response.read()
        assert body[:2] == b"PK" and len(body) == size, (
            f"下载回来的字节与磁盘文件不一致：{len(body)} vs {size}")

        assert errors == [], f"导出交互中出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# ------------------------------------------------------------------ 05 版本回滚


def test_ui_revision_restore_returns_the_disk_content_to_the_old_version(workbench_server) -> None:
    """在版本历史里恢复 rev0 → 磁盘上的 output.html **逐字节**回到 rev0。

    断言的产物：`output.html` 的字节等于首次生成时读到的字节、`.foxstate.json` 的
    revision 前进到 2、版本历史里出现「恢复自 rev0」。内存里的 rev 号变了不算数——
    v0.6.1 的教训正是「界面说成功、磁盘上是旧的」。
    """
    with workbench_server as server, sync_playwright() as playwright:
        work = pipeline.run_expert(
            "做一个带版本演进的说明页", intent_override="landing",
            output=str(server.output_root), quiet_llm=True)["work"]
        rev0 = (work / "output.html").read_bytes()

        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        node_id = _add_output_node(page, work, "landing")
        # 造一个真实的 rev1：走产品自己的反馈迭代端点，磁盘内容必须真的变。
        page.evaluate(
            """project => fetch('/api/feedback', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({project: project, note: '标题再大一点并加一段小结'})
            }).then(r => r.json())""", str(work))
        state = json.loads((work / pipeline.STATE_FILE).read_text(encoding="utf-8"))
        assert state["revision"] == 1, f"反馈后应产生 rev1，实际 rev{state['revision']}"
        assert (work / "output.html").read_bytes() != rev0, "反馈后磁盘内容没有变化，版本号是假的"
        # 产物节点自己不知道服务端已经前进到 rev1；由唯一写回入口补上。
        page.evaluate("([id, rev]) => window.FoxRevisions.advanceNodeRevision(id, rev)",
                      [node_id, state["revision"]])

        page.evaluate("openRevisionDiff(%r)" % node_id)
        page.wait_for_selector("#revision-modal:not([hidden])", timeout=20000)
        page.wait_for_function(
            "document.querySelector('#revision-history')?.textContent.includes('rev0')",
            timeout=30000)
        page.click("#revision-history li:first-child button")
        page.wait_for_function("!document.querySelector('#revision-restore').disabled", timeout=30000)
        page.click("#revision-restore")
        page.wait_for_function(
            "document.querySelector('#revision-history')?.textContent.includes('恢复自 rev0')",
            timeout=60000)

        restored = (work / "output.html").read_bytes()
        assert restored == rev0, (
            f"恢复后磁盘内容没有回到 rev0（{len(restored)} vs {len(rev0)} 字节）")
        after = json.loads((work / pipeline.STATE_FILE).read_text(encoding="utf-8"))
        assert after["revision"] == 2, f"恢复应保留原版本并前进到 rev2，实际 rev{after['revision']}"
        assert page.evaluate("id => nodes.find(n => n.id === id).data.revision", node_id) == 2

        assert errors == [], f"版本恢复交互中出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# ---------------------------------------------------------- 06 批量抓取真的发请求


def test_ui_batch_intake_button_really_reaches_the_server(workbench_server) -> None:
    """点「批量抓取」→ 服务端**真的**逐个处理了这些 URL，并给出自己的裁决。

    这是 S20 死按钮的回归防护：`intake-batch-btn` 的 `onclick="intakeFetchBatch()"`
    曾经指向一个没人实现的名字，界面上按钮还在、功能完全不可达。

    断言的产物：这次点击对应的**真实 HTTP 响应体**——`created` 为空、
    `failed` 里有每个 URL 的服务端错误码 `intake_host_forbidden`（SSRF 门禁的裁决），
    以及 `intake/candidates/` 下没有落任何候选。断掉这条接线，四个断言会同时红。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        page.evaluate("openIntake()")
        page.wait_for_selector("#intake-modal:not([hidden])", timeout=15000)
        # 批量入口收在 <details> 里，得先展开——这本身就是可达性的一层。
        page.click(".intake-more summary")
        page.fill("#intake-batch-urls", BATCH_URLS)
        with page.expect_response(
                lambda response: "/api/intake/fetch-batch" in response.url,
                timeout=60000) as response_info:
            page.click("#intake-batch-btn")
        response = response_info.value
        assert response.status == 200, f"批量抓取端点返回 HTTP {response.status}"
        payload = response.json()

        assert payload["created"] == [], f"私网地址不应被抓取成功：{payload['created']}"
        failed = {item["url"]: item for item in payload["failed"]}
        for url in BATCH_URLS.splitlines():
            assert url in failed, f"服务端没有处理这个 URL：{url}（响应 {payload}）"
            assert failed[url]["code"] == "intake_host_forbidden", \
                f"{url} 的服务端裁决不对：{failed[url]}"
        page.wait_for_function(
            "document.querySelector('#intake-status').textContent.startsWith('批量完成')",
            timeout=30000)
        assert "失败 2 个" in page.locator("#intake-status").inner_text()

        candidates = server.output_root / "intake" / "candidates"
        stored = sorted(p.name for p in candidates.iterdir()) if candidates.is_dir() else []
        assert stored == [], f"被拒绝的抓取不该留下候选文件：{stored}"

        assert errors == [], f"批量抓取交互中出现未捕获的页面 JS 错误：{errors}"
        browser.close()


# -------------------------------------------------- 07 整条旅程没有未捕获 JS 错误


def test_no_uncaught_page_errors_across_a_full_workbench_journey(workbench_server) -> None:
    """一整条真实旅程走完，`pageerror` 收集器必须是空的。

    v0.6.1 的幻灯片竞态就是这一类：HTTP 全部 200、节点照样渲染出来，只有页面里
    抛了未捕获异常。只看状态码、只看截图的门禁对它是瞎的。

    旅程：输入需求 → 分析 → 生成 → 打开/关闭导出中心 → 幻灯片原位编辑并保存 →
    打开/关闭版本历史。断言的产物：保存后磁盘上的 output.html 里真的出现了编辑文字。

    每次交互之后都先查一次 `errors` 再等结果，是有意为之：未捕获异常本身就是缺陷，
    不该等到下游的 `wait_for_function` 超时才发现——那样这条门禁就退化成了"卡住了"，
    而看不出"页面里炸了"。
    """
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = _open_workbench(page, server.base_url)

        def after(label: str) -> None:
            page.wait_for_timeout(500)
            assert errors == [], f"{label}：出现未捕获的页面 JS 错误 {errors}"

        page.get_by_role("button", name="输入需求").click()
        page.wait_for_selector("#create-modal:not([hidden])", timeout=15000)
        page.fill("#creation-prompt", BRIEF)
        after("打开输入引导")
        page.click("#creation-analyze")
        page.wait_for_selector("text=采用推荐并生成", timeout=45000)
        after("AI 分析需求")
        page.get_by_role("button", name="采用推荐并生成").click()
        # 顺序要紧：先 after() 再等产物。断线时错误当场就有，而产物永远不会出现，
        # 放在后面就是每个变异白等三分钟。
        after("采用推荐并生成")
        page.wait_for_selector(".node.output", timeout=60000)

        node_id = page.evaluate("nodes.find(node => node.kind === 'output').id")
        name = page.evaluate("id => nodes.find(n => n.id === id).data.project_name", node_id)
        _assert_a_real_artifact(server.output_root, name)
        after("生成落盘")

        # 导出中心：用真实的检查器按钮点开，不用 evaluate 代劳。派发出去的动作
        # 一旦在交互中抛错，只有走真实点击才会变成一条未捕获的页面异常——
        # evaluate 会把 rejected promise 直接抛回 Python，那是另一条路。
        # 先选中产物节点：推荐生成流程结束时选中的是需求节点，而导出入口只挂在
        # 产物检查器上（这是"点了没反应"最常见的一种原因）。
        # 按 onclick 定位而不是按按钮文案：文案在检查器的两个分支里不一样。
        page.evaluate("id => select(id)", node_id)
        page.locator('#inspector button[onclick*="openExportCenter"]').click()
        after("点开导出中心")
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'",
            timeout=60000)
        page.locator('#export-modal .preview-bar button[onclick="closeExportCenter()"]').click()
        page.wait_for_selector("#export-modal", state="hidden", timeout=20000)
        after("关闭导出中心")

        # 幻灯片原位编辑：改一个字并保存，磁盘上必须出现这个字。
        # 打开用 evaluate：幻灯片编辑入口只挂在 deck 产物的检查器上，而这条旅程
        # 的生成意图由需求决定，绑死在 deck 上会让门禁依赖意图推断的稳定性。
        # 入口是派发表里的真实动作（openSlideEditor），不是内部实现细节。
        page.evaluate("id => openSlideEditor(id)", node_id)
        page.wait_for_selector("#slides-modal:not([hidden])", timeout=20000)
        page.wait_for_function(
            "document.querySelectorAll('#slides-editor textarea').length >= 1", timeout=30000)
        first_area = page.locator("#slides-editor textarea").first
        first_area.fill(first_area.input_value() + "（已编辑）")
        page.click("#slides-save")
        after("保存幻灯片")
        page.wait_for_function(
            "document.querySelector('.fox-toast[data-toast-type=success]')"
            "?.textContent.includes('幻灯片已更新')", timeout=60000)
        assert "（已编辑）" in (server.output_root / name / "output.html").read_text(encoding="utf-8"), \
            "幻灯片保存后磁盘产物里没有编辑后的文字"
        # 保存成功后产品自己关掉编辑器（lifecycle-slides.js 的 save() 末尾会 close()），
        # 这里断言的是"真的关了"，而不是再点一次关闭按钮。
        page.wait_for_selector("#slides-modal", state="hidden", timeout=20000)
        after("保存幻灯片")

        # 版本历史：读完关闭，弹窗的关闭路径也是一条接线。
        page.locator("#btn-revision-diff").click()
        page.wait_for_selector("#revision-modal:not([hidden])", timeout=20000)
        page.wait_for_function(
            "document.querySelector('#revision-summary').textContent.length > 0", timeout=30000)
        after("打开版本历史")
        page.locator('#revision-modal button[onclick="closeRevisionDiff()"]').click()
        page.wait_for_selector("#revision-modal", state="hidden", timeout=20000)
        after("关闭版本历史")

        assert errors == [], f"整条旅程出现未捕获的页面 JS 错误：{errors}"
        browser.close()
