"""v0.6.2：补齐「功能仍在、但 v0.6.0 没有实拍」的截图门禁。

背景
----
`assets/screenshots/v0.6.0/` 只有 13 张，而 `v0.5.0/` 有 19 张在 v0.6.0 没有对应。
缺口对应的全是**没有被删除、仍在线上工作台里**的功能：输入引导、Project Memory、
命令面板、版本历史与恢复、生成取消、导出中心、两个检查器、经典模式、移动端素材库，
外加六类生成器产物。

这不是"旧图不好看"的问题，而是连锁的：README 这些功能只能挂 v0.5.0 的图、
40 秒品牌片里它们只能缺席、小红书讲它们时没有配图。

为什么单独一个文件
------------------
现有的 `e2e_verify.py` / `canvas_e2e.py` 都把输出目录写死为
`assets/screenshots/v{__version__}/` 并直接 `mkdir` + 写图——运行即污染版本化发布资产，
这正是 `docs/TEST-REPORT-v0.6.0.md` 记过的隐患。本文件不沿用该写法：
落盘目录由 `HTMLNINEFOX_V060_EVIDENCE_DIR` 决定，**未设置时只跑断言、一个字节都不写**，
因此它在 CI 上必跑且零副作用。

入口一律按当前实现查，不照抄 v0.5.0 的旧图名：
输入引导是 `openCreatePanel()` → `#create-modal`；命令面板是 `openSearch()`（Ctrl+K）
→ `#canvas-command`；不是 `#input-dialog`、也不是 `renderPalette()`（那是色卡/字体/
来源/文件/技能/产物/工作区的素材面板，不是命令面板）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from htmlninefox import pipeline

READY = ("window.FoxInteraction && window.FoxCanvasProductivity && window.FoxWorkbenchUI"
         " && window.FoxProjects && window.FoxGeneration && window.FoxRevisions"
         " && window.FoxExports && window.FoxSlides && nodes.length >= 5")

VIEWPORT = {"width": 1440, "height": 900}


def _capture(page: Page, name: str) -> None:
    evidence_dir = os.environ.get("HTMLNINEFOX_V060_EVIDENCE_DIR")
    if not evidence_dir:
        return
    target = Path(evidence_dir)
    target.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(target / name), full_page=False)


def _make(root: Path, prompt: str, intent: str | None = None) -> Path:
    return pipeline.run_expert(
        prompt, intent_override=intent,
        output=str(root), quiet_llm=True)["work"]


def _add_output_node(page: Page, project: str, title: str, intent: str) -> str:
    return page.evaluate(
        """node => {
            const ws = activeWorkspace();
            const created = addNode('output', ws.x + ws.w + 80, ws.y + 80, {
                title: node.title, project_name: node.project,
                preview_url: '/output/' + node.project + '/output.html',
                intent: node.intent, preset_id: 'fox-pixel-garden',
                revision: 0, feedback: [], workspaceId: ws.id,
            });
            select(created.id);
            return created.id;
        }""", {"title": title, "project": project, "intent": intent})


def _add_requirement_node(page: Page, text: str) -> str:
    return page.evaluate(
        """text => {
            const ws = activeWorkspace();
            const created = addNode('requirement', ws.x + 40, ws.y + ws.h + 80, {
                text: text, workspaceId: ws.id,
            });
            select(created.id);
            return created.id;
        }""", text)


# ----------------------------------------------------------------- 01 输入引导


def test_v061_input_dialog(workbench_server) -> None:
    """输入引导：统一需求入口弹窗（当前入口 openCreatePanel → #create-modal）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        page.evaluate("openCreatePanel()")
        page.wait_for_selector("#create-modal:not([hidden])", timeout=15000)
        # 可达性断言：不是拍一张空壳
        assert page.locator("#create-modal").is_visible()
        textareas = page.locator("#create-modal textarea").count()
        assert textareas >= 1, "输入引导里应至少有一个需求输入区"
        _capture(page, "input-brief.png")
        assert errors == [], f"打开输入引导出现 JS 异常：{errors}"
        browser.close()


# ------------------------------------------------------------ 02 Project Memory


def test_v061_project_memory(workbench_server) -> None:
    """Project Memory：本地保存的品牌/语气/禁忌（当前入口 openProjectMemory）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        _add_requirement_node(page, "做一个能放进行程图的作品集站点")

        page.evaluate("openProjectMemory()")
        page.wait_for_selector("#memory-modal:not([hidden])", timeout=15000)
        body = page.locator("#memory-modal").inner_text()
        assert body.strip(), "Project Memory 弹窗不应为空"
        _capture(page, "project-memory.png")
        assert errors == [], f"打开 Project Memory 出现 JS 异常：{errors}"
        browser.close()


# --------------------------------------------------------------- 03 命令面板


def test_v061_command_palette(workbench_server) -> None:
    """命令面板：Ctrl+K 打开的 #canvas-command（不是素材调色板 renderPalette）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        # openSearch() 是 canvas-productivity.js 的 IIFE 私有函数，没有挂到全局，
        # 必须走真实的 Ctrl+K 键盘路径（canvas-productivity.js:543）。
        page.click("#viewport", position={"x": 400, "y": 300})
        page.keyboard.press("Control+k")
        page.wait_for_selector("#canvas-command:not([hidden])", timeout=15000)
        # 输入一点内容，截的是「有结果的搜索态」而不是空面板
        page.fill("#canvas-command-input", "生成")
        page.wait_for_function(
            "document.querySelectorAll('#canvas-command-results *').length > 0",
            timeout=15000)
        _capture(page, "command-palette.png")
        assert errors == [], f"打开命令面板出现 JS 异常：{errors}"
        browser.close()


# ------------------------------------------------------------- 04/05 两个检查器


def test_v061_node_inspectors(workbench_server) -> None:
    """需求节点检查器与产物节点检查器（两者同属检查器，但状态与可用操作不同，分开拍）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        work = _make(server.output_root, "做一个用于说明的三栏排版落地页", "landing")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        _add_requirement_node(page, "做一个三栏排版、强调可编辑的落地页")
        inspector = page.locator("#inspector")
        inspector.wait_for(state="visible", timeout=15000)
        assert page.locator("#inspector textarea").count() >= 1, \
            "需求节点检查器应可直接编辑文字"
        _capture(page, "node-inspector.png")

        _add_output_node(page, work.name, "产物 · 三栏落地页", "landing")
        page.wait_for_function(
            "document.querySelector('#ins-rev') && document.querySelector('#ins-rev').textContent", timeout=15000)
        assert re.search(r"rev\d+", page.locator("#ins-rev").inner_text())
        _capture(page, "output-inspector.png")

        assert errors == [], f"检查器出现 JS 异常：{errors}"
        browser.close()


# ------------------------------------------------------------ 06 版本历史与恢复


def test_v061_revision_restore(workbench_server) -> None:
    """版本历史：真实产生 rev1，再打开差异对话框（当前入口 openRevisionDiff）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        work = _make(server.output_root, "做一个带版本演进的说明页", "landing")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        node_id = _add_output_node(page, work.name, "产物 · 说明页", "landing")

        # 造一个真实的 rev1。sendFeedback 从 #fb-note 读内容、不接受 note 参数，
        # 这里走 HTTP 端点造版本，再由唯一拥有者 advanceNodeRevision 写回节点。
        # 注意 /api/feedback 的 project 字段是**路径**（app.py::_feedback_request
        # 直接 Path(project)），不是项目名——传名字会静默不生效。
        page.evaluate(
            """project => fetch('/api/feedback', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({project: project, note: '标题再大一点'})
                }).then(r => r.json())""", str(work))
        new_revision = page.evaluate(
            """project => fetch('/api/projects/' + encodeURIComponent(project) + '/slides')
                .then(r => r.json()).then(d => d.revision)""", work.name)
        assert new_revision >= 1, f"反馈后应产生新版本，实际 rev{new_revision}"
        page.evaluate(
            "([id, rev]) => window.FoxRevisions.advanceNodeRevision(id, rev)",
            [node_id, new_revision])

        page.evaluate("openRevisionDiff(%r)" % node_id)
        page.wait_for_selector("#revision-modal:not([hidden])", timeout=15000)
        page.wait_for_function(
            "document.querySelector('#revision-history')?.textContent.includes('rev1')",
            timeout=20000)
        _capture(page, "revision-restore.png")
        assert errors == [], f"打开版本历史出现 JS 异常：{errors}"
        browser.close()


# ----------------------------------------------------------------- 07 生成取消


def test_v061_generation_cancel(workbench_server) -> None:
    """生成取消：#btn-cancel-gen 在生成进行中才可见，必须先真的推进一步。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        # 用服务器自带的种子需求节点推进工作区，而不是自己 addNode：
        # advanceWs 依赖工作区里已存在的需求成员，自造节点的数据形状对不上。
        page.wait_for_function(
            """() => {
                const ws = activeWorkspace();
                const req = membersOf(ws).find(n => n.kind === 'requirement')
                    || membersOf(ws).find(n => n.kind === 'note');
                if (!req) return false;
                req.data.text = '做一个可以中途取消生成的落地页';
                return true;
            }""", timeout=15000)

        assert page.locator("#btn-cancel-gen").count() == 1, \
            "取消按钮应在 DOM 中存在（不可见是正确状态）"
        assert not page.locator("#btn-cancel-gen").is_visible(), \
            "空闲时不应出现取消按钮"

        # 不做 route 拦截。advance() 在第一个 await 之前就 activeJobs.set +
        # syncCancelControl()，按钮在调用同一 tick 内即变为可见；离线生成很快，
        # 等轮询再去抓会错过窗口，所以断言与截图都紧跟在推进之后。
        # （注册 catch-all 路由反而会坏事：同步 Playwright 下路由处理器与主线程
        #   轮询共用一条连接，handler 里阻塞会让 wait_for_selector 直接卡死。）
        visible_right_after = page.evaluate(
            """() => {
                const btn = document.getElementById('btn-cancel-gen');
                advanceWs(activeWorkspace().id);
                return !btn.hidden;
            }""")
        assert visible_right_after, \
            "推进后同一 tick 内取消按钮就应可见——它由 activeJobs 非空驱动"
        _capture(page, "generation-cancel.png")
        assert errors == [], f"生成取消出现 JS 异常：{errors}"
        browser.close()


# ------------------------------------------------------------- 08/09 导出中心


def test_v061_export_center(workbench_server) -> None:
    """导出中心：deck 产物才放开 PPTX——这条正是 v0.6.0 曾整个漏掉的不变量。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        work = _make(server.output_root, "做一个用于导出演示的发布会 PPT", "deck")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        node_id = _add_output_node(page, work.name, "产物 · 导出演示", "deck")

        page.evaluate("openExportCenter(%r)" % node_id)
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'",
            timeout=45000)
        formats = [f.strip() for f in
                   page.locator("#export-format option").all_text_contents() if f.strip()]
        assert any("PDF" in f.upper() for f in formats), formats
        assert any("PNG" in f.upper() for f in formats), formats
        assert any("PPTX" in f.upper() for f in formats), \
            f"deck 产物必须能选到 PPTX（这条曾被整个漏掉）：{formats}"
        _capture(page, "export-ready.png")
        assert errors == [], f"导出中心出现 JS 异常：{errors}"
        browser.close()


def test_v061_pptx_option_is_gated_on_deck_intent(workbench_server) -> None:
    """landing 产物必须藏起 PPTX：制造一个必然失败的选项没有意义。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        work = _make(server.output_root, "做一个普通落地页用于验证格式门控", "landing")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        node_id = _add_output_node(page, work.name, "产物 · 落地页", "landing")
        page.evaluate("openExportCenter(%r)" % node_id)
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'",
            timeout=45000)
        pptx = page.locator("#export-format-pptx")
        assert pptx.count() == 1, "PPTX 选项本身应始终存在于 DOM 中"
        assert pptx.get_attribute("hidden") is not None, \
            "非 deck 产物必须藏起 PPTX 选项"
        assert page.locator("#export-format").input_value() != "pptx", \
            "非 deck 产物不应把默认格式设为 pptx"
        browser.close()


# ----------------------------------------------------------------- 10 经典模式


def test_v061_classic_mode(workbench_server) -> None:
    """经典表单模式：/classic 仍是独立路由，且仍是 Pixel Garden 品牌令牌。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/classic")
        page.wait_for_load_state("networkidle")
        assert "九尾狐" in page.content(), "经典模式页应仍是品牌页面"
        tokens = page.evaluate(
            """() => getComputedStyle(document.documentElement)
                .getPropertyValue('--accent').trim()""")
        assert tokens, "经典模式应仍使用 Pixel Garden 令牌"
        _capture(page, "classic.png")
        assert errors == [], f"经典模式出现 JS 异常：{errors}"
        browser.close()


# ------------------------------------------------------------- 11 移动端素材库


def test_v061_mobile_library(workbench_server) -> None:
    """390px 下的素材库抽屉（与移动任务视图是同一次会话里的两个状态）。"""
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)
        # 必须用真实选择器。之前按按钮文字 /素材|版式|库/ 猜，点到的不是素材库
        # 开关，拍出来是移动任务视图的节点列表——图对不上名字，等于假证据。
        toggle = page.locator("button.mobile-library-toggle")
        assert toggle.count() == 1, "窄屏应有一个素材库开关"
        toggle.click()
        # 判据用 class 而不是 offsetParent：窄屏 sidebar 是 position:fixed，
        # 而固定定位元素的 offsetParent 恒为 null，用它判断会永远等不到。
        page.wait_for_function(
            "() => document.getElementById('sidebar')"
            ".classList.contains('mobile-open')", timeout=10000)
        sidebar = page.locator("#sidebar")
        assert sidebar.is_visible(), "素材库抽屉应可见"
        # 抽到真实内容才算数：REAL HTML 模板卡是素材库的标志性内容
        assert sidebar.locator("text=REAL HTML").count() >= 1, \
            "素材库里应能看到 REAL HTML 模板卡"
        _capture(page, "mobile-library.png")
        assert errors == [], f"移动端素材库出现 JS 异常：{errors}"
        browser.close()
