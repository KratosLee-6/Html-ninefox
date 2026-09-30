"""V0.6-S20：v0.6.0 新功能实拍截图门禁（设计吸收 + 可编辑 PPTX）。

按 `docs/PLAN-v0.6.0-STABLE-20260927.md` 的 S20 与 `docs/ROADMAP.md` 第 10 节，
为 v0.6.0 独有的新功能补齐真实页面截图（v0.5.0 系列已有截图不再重拍）：

1. 素材审核台：待审候选列表 + 许可三档徽标 + 吸收指标面板
2. 审核台 CSP 沙箱预览展开态
3. 审核台「已采纳」态 + 生成风格预设 / 导入组件 / 吸收动效 按钮
4. 动效实验室 motion-lab（吸收动效 + 三档偏好）
5. 工作台内结构化幻灯片编辑对话框（S13U-b）
6. 导出中心 PPTX 导出完成态
7. 服务端 `export-report.json` 正文（可编辑元素数 + 降级清单）

截图落盘由环境变量 `HTMLNINEFOX_V060_EVIDENCE_DIR` 控制；未设置时只跑断言
不落盘（与 RC3 门禁一致，CI 上就是这种情况），因此本文件在任何环境都必跑。

所有数据都在 `tmp_path` 下离线造：审核台候选直接用 `intake` 的 store 写入，
deck 产物用 `pipeline.run_expert(..., quiet_llm=True)`（本地模板，不调 LLM），
全程不联网、不读取任何真实用户数据或 API Key。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from htmlninefox import intake, pipeline

pytest.importorskip("pptx", reason="python-pptx optional extra")

VIEWPORT = {"width": 1440, "height": 900}
READY = ("window.FoxInteraction && window.FoxIntake && window.FoxSlides && "
         "window.FoxExports && nodes.length >= 5")

# ---------------------------------------------------------------- 离线造数素材

GALLERY_BODY = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>Field Notes 落地页参考</title>
<style>body{font-family:'Satoshi',sans-serif;background:#F4F0E7;color:#17283D}
header h1{color:#173C8F}.cta{background:#49B894}</style></head>
<body><header class="site-head"><h1>Field Notes</h1><p>把调研现场带回来</p></header>
<main><section class="hero"><h2>研究即产品</h2><p>每一页都来自真实使用现场。</p></section>
<section class="pricing"><h2>价格</h2><p>按席位计费</p></section></main>
<footer class="site-foot"><p>© Field Notes</p></footer></body></html>"""

INSPIRATION_BODY = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>Motion Craft 视觉灵感板</title>
<style>body{background:#0E1B2A;color:#F4F0E7;font-family:'Space Grotesk',sans-serif}
h1{color:#49B894}</style></head>
<body><main><h1>Motion Craft</h1><p>大留白、极简字重、单色强调。</p>
<section class="gallery"><h2>版式</h2><p>仅作灵感板：只提取令牌与骨架。</p></section></main></body></html>"""

COMPONENT_BODY = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>区块组件参考</title>
<style>body{font-family:'Satoshi',sans-serif;color:#17283D}
.topnav a{color:#173C8F}.hero{background:#EDF3EC}</style></head>
<body><nav class="topnav"><a href="#">产品</a><a href="#">定价</a></nav>
<section class="hero"><h1>组件化页面骨架</h1><p>顶部导航 + 主视觉 + 页脚。</p></section>
<footer class="site-foot"><p>区块级组件参考</p></footer></body></html>"""

# animation: 900ms 会被动效预算钳制到 500ms（见 intake.MOTION_BUDGET_MS），
# transition: 300ms 保持不变——截图 4 的断言正是这一点。
MOTION_BODY = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>缓动与入场参考</title>
<style>@keyframes fadeUp{from{opacity:0}to{opacity:1}}
h1{font-family:'Satoshi',sans-serif;color:#173C8F;animation:fadeUp 900ms ease-in}
.card{transition:transform 300ms ease;box-shadow:1px 1px 0 #DFE6D9}
.card:hover{transform:translateY(-2px)}</style></head>
<body><main><h1>动作说明发生了什么</h1>
<section class="card"><h2>卡片入场</h2><p>过渡与关键帧都可被吸收。</p></section></main></body></html>"""

TYPOGRAPHY_BODY = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>开放字体排版参考</title>
<style>body{font-family:'Inter',sans-serif;font-size:16px;line-height:1.65}
h1{font-size:48px;line-height:1.1;color:#173C8F}
h2{font-size:28px;color:#49B894}</style></head>
<body><main><h1>开放字体</h1><p>Inter 排版层级参考。</p>
<section class="type-scale"><h2>字号层级</h2><p>1.1 / 1.65 行高体系。</p></section></main></body></html>"""

# (source_id, url, body, fetched_at) —— fetched_at 递增以固定列表排序
SEED_PAGES = (
    ("land-book", "https://land-book.example/website/field-notes/", GALLERY_BODY,
     "2026-09-28T09:10:00"),
    ("awwwards", "https://awwwards.example/sites/motion-craft/", INSPIRATION_BODY,
     "2026-09-28T10:20:00"),
    ("codepen-picks", "https://codepen.example/picks/block-skeleton/", COMPONENT_BODY,
     "2026-09-28T11:30:00"),
    ("animista", "https://animista.example/snippets/easing/", MOTION_BODY,
     "2026-09-28T12:40:00"),
)

# 许可第三档「开放许可」只覆盖 typography 来源（fontshare / google-fonts），
# 曾经因为 extract_typography 的形参与 KIND_EXTRACTORS 派发契约不一致而
# 一律抛 TypeError，导致该档在审核台不可达。这里无条件纳入种子并断言三档齐全，
# 任何回退都会让门禁立即失败。
TYPOGRAPHY_SEED = ("google-fonts", "https://fonts.example/specimen/inter/",
                   TYPOGRAPHY_BODY, "2026-09-28T13:50:00")


def _evidence(url: str, body: str, fetched_at: str) -> dict:
    return {
        "url": url,
        "final_url": url,
        "content_type": "text/html",
        "body": body.encode("utf-8"),
        "body_sha256": "0" * 64,
        "fetched_at": fetched_at,
    }


def _build_candidate(source: dict, url: str, body: str, fetched_at: str) -> dict:
    return intake.extract_candidate(
        _evidence(url, body, fetched_at), source=source,
        notes=f"v0.6.0 截图门禁离线样本 · {source['name']}")


def _seed_candidates(root: Path) -> tuple[dict[str, dict], set[str]]:
    """离线写入待审候选（覆盖 gallery/components/motion 与可达的许可档位）。"""
    sources = {item["id"]: item for item in intake.load_sources()}
    store = intake.CandidateStore(root)
    seeded: dict[str, dict] = {}
    pages = list(SEED_PAGES) + [TYPOGRAPHY_SEED]
    for source_id, url, body, fetched_at in pages:
        candidate = _build_candidate(sources[source_id], url, body, fetched_at)
        store.save(candidate, _evidence(url, body, fetched_at))
        seeded[source_id] = candidate
    tiers = {candidate["license_class"] for candidate in seeded.values()}
    return seeded, tiers


def _make_deck(root: Path) -> Path:
    return pipeline.run_expert(
        "做一个 AI 产品发布会 PPT，像素花园风格", intent_override="deck",
        output=str(root), quiet_llm=True)["work"]


def _capture(page: Page, name: str) -> None:
    evidence_dir = os.environ.get("HTMLNINEFOX_V060_EVIDENCE_DIR")
    if not evidence_dir:
        return
    target = Path(evidence_dir)
    target.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(target / name), full_page=False)


def _add_deck_node(page: Page, project: str) -> str:
    """把一个真实的 deck 产物挂成画布节点并选中。

    为什么用 `addNode` 而不是走引导式生成：截图门禁需要的是「已存在的 deck 产物」
    这一个前置状态，而引导式生成会额外引入 LLM 分析与 30s 生成等待，使门禁不稳定。
    这里复刻 `tests/test_pptx_export.py::test_slides_editor_dialog_edits_and_saves`
    的既有做法：节点数据全部指向 `pipeline.run_expert` 真实产出的目录，
    随后的断言（幻灯片页数、文本节点、导出报告）都从真实产物读回，
    保证截图展示的是真实工作台 DOM + 真实数据，而非占位内容。
    """
    return page.evaluate(
        """project => {
            const ws = activeWorkspace();
            const node = addNode('output', ws.x + ws.w + 80, ws.y + 60, {
                title:'AI 产品发布会 · 产物', project_name: project,
                preview_url:'/output/' + project + '/output.html',
                intent:'deck', preset_id:'fox-pixel-garden',
                revision:0, feedback:[], workspaceId:ws.id,
            });
            select(node.id);
            return node.id;
        }""", project)


# ---------------------------------------------------------------- 01-04 设计吸收 / 动效


LICENSE_LABEL = {"open": "开放许可", "reference": "仅参考重写",
                  "inspiration-only": "仅灵感板"}


def test_v060_intake_review_absorption_and_motion_lab(tmp_path: Path, workbench_server) -> None:
    seeded, tiers = _seed_candidates(tmp_path)
    total = len(seeded)
    assert total >= 4, "截图门禁至少需要 4 个离线候选覆盖三类 kind"
    assert tiers == {"open", "reference", "inspiration-only"}, (
        f"许可三档必须全部可达，实际只造出：{sorted(tiers)}")
    approved = 3
    remaining = total - approved

    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # 注意：init script 会跑进每个 frame，审核台的 sandbox 预览 iframe 没有
        # allow-same-origin，直接 localStorage.clear() 会在预览里抛错（见
        # tests/test_pptx_export.py 的同款写法），因此必须 try/catch。
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        # 顶栏「设计吸收」入口在折叠的「更多」菜单里，直接调用其全局入口函数。
        page.evaluate("openIntake()")
        page.wait_for_selector("#intake-modal:not([hidden])")
        page.wait_for_function(
            f"document.querySelectorAll('#intake-list .intake-card').length === {total}")

        # --- 截图 1：待审列表 + 许可三档徽标 + 吸收指标面板
        badges = page.locator("#intake-list .intake-badge").all_inner_texts()
        assert len(badges) >= total, "每个候选卡都应至少渲染一个许可徽标"
        for tier in tiers:
            assert LICENSE_LABEL[tier] in badges, \
                f"审核台未显示「{LICENSE_LABEL[tier]}」许可档位徽标，实际徽标：{badges}"
        assert page.locator("#intake-list .intake-swatch").count() >= 6, "候选应展示设计令牌色板"
        assert page.locator("#intake-list .intake-outline").count() >= 3, "候选应展示骨架大纲"
        # 吸收指标已从一行内联调试串改为指标条（数字在上、标签在下），
        # 所以这里断言「信息在不在」，不再断言旧的串式排版。
        stats = page.locator("#intake-stats").inner_text()
        assert "吸收指标" in stats, stats
        metrics = page.evaluate("""() => Object.fromEntries(
            [...document.querySelectorAll('#intake-stats .intake-metric')]
              .map(m => [m.querySelector('span').textContent.trim(),
                         m.querySelector('b').textContent.trim()]))""")
        assert metrics.get("候选") == str(total), f"候选数不符：{metrics}"
        assert metrics.get("待审") == str(total), f"待审数不符：{metrics}"
        assert "google-fonts" in stats, f"吸收指标面板缺少来源分布：{stats}"
        _capture(page, "intake-review-pending.png")

        # --- 截图 2：沙箱预览展开态
        component_id = seeded["codepen-picks"]["candidate_id"]
        card = page.locator(f"#intake-list .intake-card", has_text="区块组件参考")
        assert card.count() == 1, "审核台应能按标题定位到组件类候选"
        card.locator("button", has_text="预览").click()
        frame = page.locator(f"#intake-preview-{component_id}")
        page.wait_for_selector(f"#intake-preview-{component_id}:not([hidden])")
        assert frame.is_visible(), "沙箱预览 iframe 应在点击「预览」后展开"
        assert "allow-scripts" not in (frame.get_attribute("sandbox") or "")
        assert frame.get_attribute("src") == f"/api/intake/candidates/{component_id}/preview"
        # 预览由服务端 CSP 兜底：不执行脚本、样式仅内联。
        with urllib.request.urlopen(
                server.base_url + frame.get_attribute("src"), timeout=10) as raw:
            preview_html = raw.read().decode("utf-8")
            assert raw.headers["Content-Security-Policy"] == (
                "default-src 'none'; style-src 'unsafe-inline'; img-src data:")
            assert "<script" not in preview_html.lower()
        frame.scroll_into_view_if_needed()
        _capture(page, "intake-preview-sandbox.png")

        # --- 截图 3：已采纳态 + 生成风格预设 / 导入组件 / 吸收动效
        page.locator("#intake-modal .flow-body").evaluate("el => el.scrollTop = 0")
        for index, source_id in enumerate(("land-book", "codepen-picks", "animista"), start=1):
            title = seeded[source_id]["title"]
            card = page.locator("#intake-list .intake-card", has_text=title)
            assert card.count() == 1, f"待审列表里找不到候选：{title}"
            card.locator("button", has_text="采纳为模板").click()
            # 每次采纳都会重拉列表（中途会清空成「读取候选素材…」占位），
            # 因此必须等到「剩余卡片数正确且占位已消失」再进行下一次点击。
            page.wait_for_function(
                "count => document.querySelectorAll('#intake-list .intake-card').length === count"
                " && !document.querySelector('#intake-list .analysis-empty')",
                arg=total - index)
        page.wait_for_function(
            f"document.querySelectorAll('#intake-list .intake-card').length === {remaining}")
        assert page.locator(".fox-toast[data-toast-type='success']").count() >= 1, "采纳应给出成功提示"

        page.locator(".intake-toolbar button", has_text="已采纳").click()
        page.wait_for_function(
            f"document.querySelectorAll('#intake-list .intake-card').length === {approved}")
        approved_text = page.locator("#intake-list").inner_text()
        assert "已拒绝" not in approved_text

        preset_card = page.locator("#intake-list .intake-card", has_text="Field Notes 落地页参考")
        component_card = page.locator("#intake-list .intake-card", has_text="区块组件参考")
        motion_card = page.locator("#intake-list .intake-card", has_text="缓动与入场参考")
        assert preset_card.locator("button", has_text="生成风格预设").count() == 1
        assert component_card.locator("button", has_text="导入组件").count() == 1
        assert motion_card.locator("button", has_text="吸收动效").count() == 1
        # 非对应 kind 的候选不出现组件/动效按钮
        assert preset_card.locator("button", has_text="导入组件").count() == 0
        assert motion_card.locator("button", has_text="生成风格预设").count() == 1

        # 指标面板已改为指标条，断言走数据而不是排版字符串
        def metrics() -> dict[str, str]:
            return page.evaluate("""() => Object.fromEntries(
                [...document.querySelectorAll('#intake-stats .intake-metric')]
                  .map(m => [m.querySelector('span').textContent.trim(),
                             m.querySelector('b').textContent.trim()]))""")

        preset_card.locator("button", has_text="生成风格预设").click()
        page.wait_for_function(
            "document.querySelectorAll('#intake-stats .intake-metric').length >= 7"
            " && [...document.querySelectorAll('#intake-stats .intake-metric')]"
            "    .some(m => m.querySelector('span').textContent.trim() === '风格预设'"
            "       && m.querySelector('b').textContent.trim() === '1')")
        component_card.locator("button", has_text="导入组件").click()
        page.wait_for_function(
            "[...document.querySelectorAll('#intake-stats .intake-metric')]"
            "  .some(m => m.querySelector('span').textContent.trim() === '组件'"
            "     && m.querySelector('b').textContent.trim() === '3')")
        motion_card.locator("button", has_text="吸收动效").click()
        page.wait_for_function(
            "[...document.querySelectorAll('#intake-stats .intake-metric')]"
            "  .some(m => m.querySelector('span').textContent.trim() === '动效'"
            "     && m.querySelector('b').textContent.trim() === '1')")

        final = metrics()
        assert final.get("已采纳") == str(approved), final
        assert final.get("待审") == str(remaining), final
        assert (final.get("组件"), final.get("动效"), final.get("风格预设")) == ("3", "1", "1"), final
        # 关掉最早两条「已采纳」提示，避免遮挡指标面板（保留本次三条吸收动作的提示）
        for _ in range(2):
            page.locator(".fox-toast .fox-toast-close").first.click()
        page.wait_for_timeout(220)
        _capture(page, "intake-approved-absorption.png")
        page.evaluate("closeIntake()")

        # --- 截图 4：动效实验室（吸收到的原创动效 + 三档偏好）
        lab = browser.new_page(viewport=VIEWPORT)
        lab_errors: list[str] = []
        lab.on("pageerror", lambda error: lab_errors.append(str(error)))
        lab.goto(server.base_url + "/motion-lab")
        lab.wait_for_selector("#intake-motion-box .tile")
        lab.wait_for_function(
            "document.querySelectorAll('#intake-motion-box .tile').length >= 1")
        lab_box = lab.locator("#intake-motion-box").inner_text()
        assert "缓动与入场参考" in lab_box, f"motion-lab 未展示吸收到的动效：{lab_box}"
        # 900ms 被钳制到 500ms、300ms 保持原值（动效预算 S10）
        assert "500ms" in lab_box and "300ms" in lab_box, lab_box
        assert "设计吸收动效" in lab.locator("section.card", has_text="设计吸收动效").inner_text()

        assert "此页为交互样例，不创建项目或提交生成任务" in lab.locator("#status").inner_text()

        lab.select_option("[data-motion-preference]", "reduced")
        lab.wait_for_function(
            "document.documentElement.dataset.foxMotion === 'reduced'")
        lab.locator("button", has_text="重播吸收动效").click()
        lab.wait_for_function(
            "document.querySelector('#status').textContent.includes('当前动效：reduced')")
        assert "已演示：重播吸收动效" in lab.locator("#status").inner_text()
        # 让 v0.6.0 新增的 07 号卡片与状态行落在视口内
        lab.evaluate(
            """() => {
                const card = document.querySelector('#intake-motion-box').closest('section');
                window.scrollTo(0, card.getBoundingClientRect().top + window.scrollY - 90);
            }""")
        lab.wait_for_timeout(200)
        _capture(lab, "motion-lab-intake-motion.png")
        assert not lab_errors, f"motion-lab 出现 JS 异常：{lab_errors}"
        lab.close()

        assert not errors, f"工作台出现 JS 异常：{errors}"
        browser.close()


# ---------------------------------------------------------------- 05 幻灯片编辑对话框


def test_v060_slide_editor_dialog(tmp_path: Path, workbench_server) -> None:
    work = _make_deck(tmp_path)
    assert (work / "output.html").is_file()

    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        node_id = _add_deck_node(page, work.name)
        # 节点是真实产物：画布里能读到 deck 语义与项目名
        assert page.evaluate(
            """([id, name]) => {
                const node = nodes.find(item => item.id === id);
                return Boolean(node && node.kind === 'output' && node.data.intent === 'deck'
                               && node.data.project_name === name);
            }""", [node_id, work.name])
        page.wait_for_selector("#inspector button:has-text('编辑幻灯片')")
        assert page.locator("#ins-rev").inner_text() == "rev0"

        # 从检查器按钮进入（真实 UI 路径）
        page.locator("#inspector button", has_text="编辑幻灯片").click()
        page.wait_for_selector("#slides-modal:not([hidden])")
        page.wait_for_function(
            "document.querySelectorAll('#slides-editor .slides-slide').length >= 5")
        assert work.name in page.locator("#slides-title").inner_text()

        slide_blocks = page.locator("#slides-editor .slides-slide")
        page.wait_for_function(
            "document.querySelectorAll('#slides-editor textarea[data-slide]').length > 0")
        areas = page.locator("#slides-editor textarea[data-slide][data-node]")
        for index in range(slide_blocks.count()):
            assert slide_blocks.nth(index).locator("textarea[data-slide]").count() >= 1, \
                f"第 {index + 1} 页没有任何可编辑文本节点"
        assert slide_blocks.count() >= 5, "deck 产物应有多页可编辑"
        status = page.locator("#slides-status").inner_text()
        assert re.search(r"共 \d+ 页 · 修订基于 rev\d+", status), status
        assert f"共 {slide_blocks.count()} 页" in status, status
        # 对话框渲染的文本节点数必须与幻灯片 API 返回的完全一致
        assert areas.count() == page.evaluate(
            "fetch('/api/projects/' + encodeURIComponent(%s) + '/slides')"
            ".then(r => r.json()).then(d => d.slides.reduce((n, s) => n + s.texts.length, 0))"
            % json.dumps(work.name))
        assert page.locator("#slides-save").is_enabled()
        _capture(page, "slide-editor-dialog.png")

        # 编辑 → 保存为新版本（编辑闭环真实生效）
        first = areas.first
        original = first.input_value()
        first.fill(original + "（v0.6.0 已编辑）")
        page.locator("#slides-save").click()
        page.wait_for_function(
            "document.querySelector('.fox-toast[data-toast-type=success]')"
            "?.textContent.includes('幻灯片已更新')")
        assert "（v0.6.0 已编辑）" in (work / "output.html").read_text(encoding="utf-8")
        assert "rev1" in page.locator("#ins-rev").inner_text()
        assert not errors, f"幻灯片编辑出现 JS 异常：{errors}"
        browser.close()


# ---------------------------------------------------------------- 06-07 PPTX 导出报告


def test_v060_pptx_export_report(tmp_path: Path, workbench_server) -> None:
    work = _make_deck(tmp_path)
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("try{localStorage.clear()}catch(e){}")
        page.goto(server.base_url + "/")
        page.wait_for_function(READY)

        node_id = _add_deck_node(page, work.name)
        page.evaluate("openExportCenter(%s)" % node_id)
        page.wait_for_selector("#export-modal:not([hidden])")
        page.wait_for_function(
            "document.querySelector('#export-status').textContent === '分析完成，可以导出'")
        assert "检测到" in page.locator("#export-analysis").inner_text()

        # 格式下拉的 PPTX 选项由 index.html 登记，renderAnalysis 只在 deck 产物
        # 放开（服务端对非 deck 直接报错），因此这里断言选项真实可选中，
        # 不再向页面注入任何临时 option。<option> 没有独立布局盒，is_hidden()
        # 不可靠，直接查 hidden 属性与可选值。
        assert page.evaluate("document.querySelector('#export-format-pptx').hidden") is False, \
            "deck 产物应放开 PPTX 格式"
        assert page.evaluate(
            "[...document.querySelector('#export-format').options]"
            ".some(o => o.value === 'pptx')"), "格式下拉应包含 pptx 选项"
        page.select_option("#export-format", "pptx")
        page.wait_for_function(
            "document.querySelector('#export-paper-field').hidden === true")
        page.locator("#export-start").click()
        page.wait_for_function(
            "document.querySelector('#export-status').textContent.startsWith('导出完成')",
            timeout=60000)
        status = page.locator("#export-status").inner_text()
        assert "python-pptx" in status, status
        rows = page.locator("#export-result .export-file")
        assert rows.count() == 2, "导出结果应恰好含 pptx 与报告两行（不得重复渲染报告）"
        links = page.eval_on_selector_all(
            "#export-result a", "els => els.map(e => e.getAttribute('href'))")
        assert all(href and "undefined" not in href for href in links), links
        assert len(links) == 2, links
        _capture(page, "export-center-pptx.png")

        report_path = next(href for href in links
                           if href and "export-report.json" in href).split("?")[0]
        report = json.loads(
            urllib.request.urlopen(server.base_url + report_path, timeout=15)
            .read().decode("utf-8"))
        assert report["browser"]["engine"] == "python-pptx"
        assert report["pptx"]["editable_elements"] > 0, "导出报告必须给出可编辑元素数"
        assert report["pptx"]["slides"] >= 5
        downgrades = [item for item in report["warnings"] if item["code"] == "pptx_flattened"]
        assert downgrades and "扁平化视觉元素" in downgrades[0]["message"], report["warnings"]
        assert any(file["name"].endswith(".pptx") for file in report["files"])
        assert Path(work.name + ".pptx").name in {Path(f["name"]).name for f in report["files"]}

        # --- 截图 7：报告正文（可编辑元素数 + 降级清单）由服务端真实提供
        report_page = browser.new_page(viewport=VIEWPORT)
        report_errors: list[str] = []
        report_page.on("pageerror", lambda error: report_errors.append(str(error)))
        report_page.goto(server.base_url + report_path)
        report_page.wait_for_function("document.body.innerText.includes('editable_elements')")
        body_text = report_page.locator("body").inner_text()
        assert "python-pptx" in body_text
        assert "pptx_flattened" in body_text, "报告正文应包含降级清单条目"
        _capture(report_page, "pptx-export-report.png")
        assert not report_errors, f"报告页出现 JS 异常：{report_errors}"
        report_page.close()

        assert not errors, f"导出中心出现 JS 异常：{errors}"
        browser.close()
