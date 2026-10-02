"""v0.6 / RC3-E: isolated workbench lifecycle modules, race guards, and cancel."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from htmlninefox import intake, pipeline

READY = ("window.FoxInteraction && window.FoxCanvasProductivity && window.FoxWorkbenchUI"
         " && window.FoxProjects && window.FoxGeneration && window.FoxRevisions"
         " && window.FoxExports && nodes.length >= 5")


def _capture(page, name: str) -> None:
    evidence_dir = os.environ.get("HTMLNINEFOX_RC3_EVIDENCE_DIR")
    if not evidence_dir:
        return
    target = Path(evidence_dir)
    target.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(target / name), full_page=False)


def _wait_for_requirement_text(page, text: str) -> None:
    page.wait_for_function(
        """text => {
            const ws = activeWorkspace();
            const req = membersOf(ws).find(n => n.kind === 'requirement')
                || membersOf(ws).find(n => n.kind === 'note');
            if (!req) return false;
            req.data.text = text;
            const el = document.getElementById('node-' + req.id);
            const area = el && el.querySelector('textarea');
            if (area) area.value = text;
            return true;
        }""", arg=text)


def test_lifecycle_modules_expose_namespaced_apis_and_global_shims(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        apis = page.evaluate(
            """() => ({
                projects: Object.keys(window.FoxProjects).sort(),
                generation: Object.keys(window.FoxGeneration).sort(),
                revisions: Object.keys(window.FoxRevisions).sort(),
                exports: Object.keys(window.FoxExports).sort(),
                shims: [typeof openRevisionDiff, typeof openExportCenter,
                        typeof advanceWs, typeof startExport, typeof cancelGeneration],
                draftsPrivate: [typeof exportDraft, typeof revisionDraft],
            })"""
        )
        assert "load" in apis["projects"] and "trash" in apis["projects"]
        assert "advance" in apis["generation"] and "cancelActive" in apis["generation"]
        assert "restore" in apis["revisions"] and "sendFeedback" in apis["revisions"]
        assert "start" in apis["exports"] and "draft" in apis["exports"]
        assert apis["shims"] == ["function", "function", "function", "function", "function"]
        # Module draft state is no longer a global variable.
        assert apis["draftsPrivate"] == ["undefined", "undefined"]
        assert errors == []
        browser.close()


def test_rapid_double_advance_is_rejected_and_produces_one_result(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        _wait_for_requirement_text(page, "做一个极简的落地页，介绍本地优先的 HTML 工作台")

        ws_id = page.evaluate("activeWorkspace().id")
        # 生成走 POST /api/jobs（lifecycle-generation.js），轮询是 GET /api/jobs/{id}，按方法与路径分别计数。
        submitted_jobs: list[str] = []
        page.on("request", lambda request: submitted_jobs.append(request.url)
                if request.method == "POST" and request.url.endswith("/api/jobs") else None)

        # 两次推进必须在同一个 evaluate 里同步发出。
        # 之前是两个 page.evaluate 往返：中间隔着一次网络往返，第一次推进的
        # 任务轮询器（lifecycle-generation.js 里写 #tl-status 的那个）有机会先把
        # 守卫提示覆盖掉，断言就永远等不到——这是该用例在 CI 上反复超时的原因，
        # 而本地因为机器快、窗口小而复现不出来。
        # advance() 在第一个 await 之前就同步写了 activeJobs，所以同步连发两次
        # 时第二次必然命中守卫，且此刻首次轮询还没开始，提示不会被覆盖。
        guard_fired = page.evaluate(
            """id => {
                void advanceWs(id);
                void advanceWs(id);
                return document.querySelector('#tl-status').textContent
                    .includes('该工作区正在推进');
            }""", ws_id)
        assert guard_fired, "同一次任务内第二次推进应被 epoch 守卫立即拒绝"

        page.wait_for_selector(".node.output", timeout=30000)
        page.wait_for_function("document.querySelectorAll('.node.output').length === 1")
        page.wait_for_function(
            "FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")
        # 守卫真正要保证的不变量：被拒绝的那次不产生第二个任务。
        assert len(submitted_jobs) == 1, (
            f"守卫应只放行一次生成，实际提交 {len(submitted_jobs)} 次：{submitted_jobs}")
        assert not page.locator("#btn-cancel-gen").is_visible()
        assert errors == []
        browser.close()


def test_cancel_generation_aborts_waiting_with_honest_feedback(
        tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")

        # 让任务提交响应停在路上，保证取消点确定落在等待阶段
        def hold_submit(route):
            if "api/jobs" in route.request.url and route.request.method == "POST":
                page.wait_for_timeout(1200)
            route.continue_()

        page.route("**/*", hold_submit)
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        _wait_for_requirement_text(page, "做一个取消演示落地页")

        ws_id = page.evaluate("activeWorkspace().id")
        page.evaluate("id => void advanceWs(id)", ws_id)
        page.wait_for_selector("#btn-cancel-gen:not([hidden])")
        page.locator("#btn-cancel-gen").click()

        page.wait_for_function(
            "document.querySelector('#tl-status').textContent.includes('已停止等待本次生成')")
        page.wait_for_function("!document.getElementById('btn-cancel-gen').offsetParent")
        page.wait_for_function(
            "FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")
        _capture(page, "generation-cancel.png")
        assert page.locator(".node.output").count() == 0
        assert errors == []
        browser.close()


def test_export_start_is_guarded_while_a_job_is_running(tmp_path, workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")

        work = pipeline.run_expert(
            "做一个导出守卫演示落地页", output=str(server.output_root), quiet_llm=True)["work"]
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        node_id = page.evaluate(
            """project => {
                const ws = activeWorkspace();
                const node = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                    title:'导出守卫 · 产物', project_name: project,
                    preview_url:'/output/' + project + '/output.html',
                    intent:'landing', preset_id:'fox-pixel-garden',
                    revision:0, feedback:[], workspaceId:ws.id,
                });
                select(node.id);
                return node.id;
            }""", work.name)

        def hold_export(route):
            if "api/exports" in route.request.url and route.request.method == "POST":
                page.wait_for_timeout(1000)
            route.continue_()

        page.route("**/*", hold_export)
        page.evaluate("nodeId => openExportCenter(nodeId)", node_id)
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'")
        page.locator("#export-start").click()
        page.wait_for_function("!document.getElementById('export-start').disabled === false")
        # busy 守卫：进行中再次触发 start 直接被拒，不提交第二个任务
        busy_flash = page.evaluate(
            "() => { FoxExports.start(); return document.querySelector('#tl-status').textContent; }")
        assert "已有导出正在进行" in busy_flash
        page.wait_for_function(
            "document.querySelector('#export-status').textContent.includes('导出完成')", timeout=60000)
        page.unroute("**/*", hold_export)
        assert not page.locator("#export-start").is_disabled()
        assert errors == []
        browser.close()


def test_slides_open_discards_stale_response(tmp_path, workbench_server):
    """交错打开两个 deck 时，先发出的那次 GET 不得覆盖后一次的 draft。

    缺陷形态：`open()` 在 await 之后无保护地写 `draft.revision` / `draft.slides`，
    而 `open()` 开头会把 draft 整体重写。于是「打开 A → GET 在途 → 打开 B →
    A 的 GET 返回」会把 A 的幻灯片与 revision 写进 B 的 draft，随后保存时
    `advanceNodeRevision(B, A 的 revision)` 把 revision 写进了另一个节点。
    原有守卫只有 `draft.busy`，它只挡保存按钮重复点击，对这个交错毫无作用。
    """
    slides_ready = ("window.FoxInteraction && window.FoxSlides && nodes.length >= 5")
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("localStorage.clear()")

        first = pipeline.run_expert(
            "做一个甲号产品发布会 PPT", intent_override="deck",
            output=str(server.output_root), quiet_llm=True)["work"]
        second = pipeline.run_expert(
            "做一个乙号季度复盘发布会 PPT", intent_override="deck",
            output=str(server.output_root), quiet_llm=True)["work"]

        def add_deck_node(project: str, title: str) -> str:
            return page.evaluate(
                """project => {
                    const ws = activeWorkspace();
                    const node = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                        title: project, project_name: project,
                        preview_url: '/output/' + project + '/output.html',
                        intent: 'deck', preset_id: 'fox-pixel-garden',
                        revision: 0, feedback: [], workspaceId: ws.id,
                    });
                    select(node.id);
                    return node.id;
                }""", project)

        page.goto(server.base_url + "/")
        page.wait_for_function(slides_ready)
        add_deck_node(first.name, "甲号")
        add_deck_node(second.name, "乙号")

        # 让甲号的 slides 响应慢一拍，从而稳定复现「先发后到」的交错。
        # 慢的必须是先发的那次，否则守卫无意义。
        def delay_first_slides(route):
            if "/slides" in route.request.url and first.name in route.request.url:
                page.wait_for_timeout(1200)
            route.continue_()

        page.route("**/*", delay_first_slides)
        # 两次 open 必须在同一次 evaluate 里同步发出：两次往返之间隔着网络
        # 往返，慢的那次可能已经返回，交错就复现不出来（同 test_rapid_double_advance
        # 的教训）。open() 在第一个 await 之前就同步重写了 draft。
        page.evaluate(
            """pair => { void FoxSlides.open(pair[0]); void FoxSlides.open(pair[1]); }""",
            [first.name and _node_id_for(page, first.name),
             _node_id_for(page, second.name)])

        page.wait_for_function(
            "document.querySelectorAll('#slides-editor .slides-slide').length > 0",
            timeout=30000)
        # 让被延迟的甲号响应落地
        page.wait_for_timeout(2500)

        title = page.locator("#slides-title").inner_text()
        # 精确匹配而不是子串：两次 run_expert 若落在同一秒，产物名会是
        # html9n-<ts> 与 html9n-<ts>-2，后者包含前者，子串断言会假失败。
        assert title == "幻灯片编辑 · " + second.name, (
            f"后打开的 deck 应留在编辑器里，实际是：{title}")

        # 真正的不变量：渲染出来的**内容**必须属于第二个 deck。
        # 标题是 open() 同步写的，天然属于第二个 deck，不足以作证据。
        # 比对页数也不行——两个 deck 同为 deck 意图，页数很可能相同，
        # 那样旧响应覆盖后页数照样对得上，断言就成了摆设（本次就是这么假通过的）。
        # 比对首个文本节点同样不行——deck 生成器把封面写成固定的
        # 「Your Product · 发布会 2026」，两个 deck 完全一样。
        # 因此比对**全部可编辑文本**的拼接结果。
        join_slides = """project => fetch('/api/projects/' + encodeURIComponent(project) + '/slides')
            .then(r => r.json())
            .then(d => d.slides.map(s => s.texts.map(t => t.node + '=' + t.text).join('|'))
                              .join('||'))"""
        expected_text = page.evaluate(join_slides, second.name)
        stale_text = page.evaluate(join_slides, first.name)
        assert expected_text != stale_text, (
            "两个 deck 的全部可编辑文本必须不同，否则本用例无法区分新旧状态")
        rendered_text = page.evaluate(
            """() => {
                // 必须与服务端序列化同构：按页分组、页内用 | 、页间用 ||
                // 之前把全部 textarea 直接用 | 拼，导致与 expected 格式不同、
                // 断言恒假，是这条门禁自己的 bug。
                const bySlide = new Map();
                for (const a of document.querySelectorAll(
                        '#slides-editor textarea[data-slide][data-node]')) {
                    const k = a.dataset.slide;
                    if (!bySlide.has(k)) bySlide.set(k, []);
                    bySlide.get(k).push(a.dataset.node + '=' + a.value);
                }
                return Array.from(bySlide.values()).map(v => v.join('|')).join('||');
            }""")
        assert rendered_text == expected_text, (
            f"编辑器渲染的是另一个 deck 的内容（首个差异位置）：\n"
            f"  期望(第二个)={_first_diff(expected_text, rendered_text)}"
            f"\n  实际        ={_first_diff(rendered_text, expected_text)}"
            f"\n  先发后到的   ={_first_diff(stale_text, expected_text)}")
        assert re.search(r"共 \d+ 页 · 修订基于 rev\d+",
                         page.locator("#slides-status").inner_text())

        page.unroute("**/*", delay_first_slides)
        assert errors == []
        browser.close()


def _first_diff(a: str, b: str) -> str:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"…{a[max(0, i - 30):i + 30]}… vs …{b[max(0, i - 30):i + 30]}…"
    return f"(长度 {len(a)} vs {len(b)})"


def _node_id_for(page, project_name: str) -> str:
    return page.evaluate(
        "name => nodes.find(n => n.data && n.data.project_name === name).id",
        project_name)


def test_intake_workbench_dialog_lists_candidates(tmp_path: Path, workbench_server) -> None:
    sample = (b"<!doctype html><html><head><title>UI Inspo Board</title>"
              b"<style>body{color:#173C8F}</style></head><body><main><h1>Board</h1></main></body></html>")
    evidence = {
        "url": "https://example.com/board", "final_url": "https://example.com/board",
        "followed": ["https://example.com/board"], "status": 200,
        "content_type": "text/html", "body": sample, "body_sha256": "1" * 64,
        "body_bytes": len(sample), "fetched_at": "2026-09-26T09:00:00",
    }
    candidate = intake.extract_candidate(
        evidence, source={"id": "land-book", "license_class": "reference"})
    with workbench_server as server:
        intake.CandidateStore(server.output_root).save(candidate, evidence)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            # 沙箱预览 iframe 是不透明源，localStorage 不可用——init 脚本需容错
            page.add_init_script("try{localStorage.clear()}catch(e){}")
            page.goto(server.base_url + "/")
            page.wait_for_function(
                "window.FoxInteraction && window.FoxIntake && nodes.length >= 5")
            page.evaluate("openIntake()")
            page.wait_for_selector("#intake-modal:not([hidden])")
            page.wait_for_function(
                "document.querySelector('#intake-list').textContent.includes('UI Inspo Board')")
            assert page.locator(".intake-card").count() == 1
            assert page.locator("#intake-source option").count() >= 3
            _capture(page, "intake-review.png")
            assert errors == []
            browser.close()
