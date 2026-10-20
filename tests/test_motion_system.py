"""Motion preferences and lifecycle must never alter business state or focus."""

import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture
def workbench(workbench_server):
    with workbench_server as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            try:
                page.goto(server.base_url)
                page.wait_for_function("window.FoxMotion && window.FoxCanvasProductivity && nodes.length >= 4")
                yield page, server.base_url
                assert not errors
            finally:
                browser.close()


def test_motion_preferences_follow_system_and_persist(workbench):
    page, base = workbench
    assert page.locator("html").get_attribute("data-fox-motion") == "full"
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_function("document.documentElement.dataset.foxMotion === 'reduced'")
    page.evaluate("""() => {
        FoxInteraction.setBusy('#btn-create', true);
        flash('减少动效仍显示状态', true);
        const node = nodes.find(n => n.kind === 'requirement');
        markNodeGenerating(node.id, 47);
        window.motionNodeId = node.id;
    }""")
    assert page.locator("[data-gen-ring] .gen-ring-pct").inner_text() == "47%"
    assert page.evaluate("getComputedStyle(document.querySelector('#btn-create'),'::before').animationName") == "none"
    assert page.evaluate("getComputedStyle(document.querySelector('.fox-toast')).transitionDuration") == "0s"
    assert page.evaluate("FoxMotion.activeCount") == 0
    page.emulate_media(reduced_motion="no-preference")
    page.wait_for_function("document.documentElement.dataset.foxMotion === 'full'")
    page.locator("#motion-preference").select_option("off")
    page.reload()
    page.wait_for_function("window.FoxCanvasProductivity && window.FoxMotion")
    assert page.locator("#motion-preference").input_value() == "off"
    assert page.locator("html").get_attribute("data-fox-motion") == "off"
    page.locator("#btn-create").click()
    page.wait_for_function("document.activeElement?.id === 'creation-prompt'")
    page.keyboard.press("Escape")
    page.wait_for_function("document.activeElement?.id === 'btn-create'")
    # CSS policy and persisted preference also apply to the locally packaged sample page.
    page.goto(base + "/motion-lab")
    page.locator('[data-demo="result"]').click()
    assert page.locator("html").get_attribute("data-fox-motion") == "off"
    assert page.evaluate("FoxMotion.activeCount") == 0


def test_retry_survives_old_failure_and_success_cleanup(workbench):
    page, _ = workbench
    node_id = page.evaluate("""() => {
        const node = nodes.find(n => n.kind === 'requirement');
        markNodeGenerating(node.id, 10); finishNodeGenerating(node.id, true);
        markNodeGenerating(node.id, 61);
        // Replacement DOM must not revive an old cleanup or drop the current badge.
        document.getElementById('node-' + node.id).remove(); renderNode(node);
        return node.id;
    }""")
    page.wait_for_timeout(2750)
    assert page.locator(f"#node-{node_id} .gen-ring-pct").inner_text() == "61%"
    assert page.evaluate("FoxGeneration.generatingNodes.get(%d).status" % node_id) == "running"
    page.evaluate("""id => {
        finishNodeGenerating(id, false); markNodeGenerating(id, 72);
    }""", node_id)
    page.wait_for_timeout(450)
    assert page.locator(f"#node-{node_id} .gen-ring-pct").inner_text() == "72%"
    assert page.evaluate("FoxGeneration.generationCleanups.size") == 0
    page.evaluate("""id => {
        finishNodeGenerating(id, true);
        nodes = nodes.filter(node => node.id !== id);
        document.getElementById('node-' + id).remove();
    }""", node_id)
    page.wait_for_function("FoxGeneration.generatingNodes.size === 0 && FoxGeneration.generationCleanups.size === 0")


def test_motion_interruptions_budget_and_dialog_focus(workbench):
    page, _ = workbench
    page.wait_for_function("FoxMotion.activeCount === 0")
    result = page.evaluate("""() => {
        const host = document.createElement('div');host.id='motion-test';
        host.style.cssText='position:fixed;top:80px;left:20px;z-index:999';
        document.body.appendChild(host);
        for(let i=0;i<20;i++){
            const element=document.createElement('div');element.textContent='target';host.appendChild(element);
            FoxMotion.play('reveal',element);
        }
        const active=FoxMotion.activeCount;host.remove();return active;
    }""")
    assert 0 < result <= 8
    page.wait_for_function("FoxMotion.activeCount === 0")
    page.evaluate("""() => {
        const node=document.querySelector('.node');
        for(let i=0;i<100;i++)FoxMotion.animateClass(node,'node-enter','fox-node-enter');
        FoxMotion.setPreference('reduced');
    }""")
    assert page.evaluate("FoxMotion.activeCount") == 0
    assert page.locator(".node-enter").count() == 0
    page.evaluate("""() => {
        FoxMotion.setPreference('system');
        document.querySelector('#btn-create').focus();
        for(let i=0;i<100;i++){openCreatePanel();FoxInteraction.closeDialog('#create-modal');}
    }""")
    page.wait_for_function("document.activeElement.id === 'btn-create'")
    assert page.locator("#create-modal").is_hidden()
    assert page.evaluate("FoxMotion.activeCount") == 0


def test_progress_coalesces_toasts_and_sample_has_mobile_layout(workbench):
    page, base = workbench
    result = page.evaluate("""() => {
        document.querySelector('#toast-region').replaceChildren();
        const report=createJobProgressReporter('测试生成');
        for(let progress=1;progress<100;progress++)report({stage:'generate',progress});
        report({stage:'verify',progress:100});
        return {count:document.querySelectorAll('.fox-toast').length,text:document.querySelector('#tl-status').textContent};
    }""")
    assert result == {"count": 2, "text": "测试生成 · 质量验证 · 100%"}
    page.evaluate("for(let i=0;i<20;i++)FoxInteraction.notify('消息'+i)")
    assert page.locator(".fox-toast").count() == 4
    page.goto(base + "/motion-lab")
    for kind in ["button", "selection", "wire", "stage", "result", "revision"]:
        page.locator(f'[data-demo="{kind}"]').click()
    assert page.locator("#selection-demo").inner_text() == "✓ 模板 A 已选"
    assert page.locator("#stage-demo").inner_text() == "组合输入"
    assert page.locator("#revision-demo").inner_text() == "rev2 · 恢复自 rev0"
    page.wait_for_function("FoxMotion.activeCount === 0")
    evidence = os.environ.get("HTMLNINEFOX_TEST_EVIDENCE_DIR")
    if evidence:
        Path(evidence).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(evidence) / "motion-lab-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if evidence:
        page.screenshot(path=str(Path(evidence) / "motion-lab-mobile.png"), full_page=True)
    page.goto(base)
    page.wait_for_function("window.FoxMotion && window.FoxCanvasProductivity")
    bounds = page.locator("#motion-preference").bounding_box()
    assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390


# ---- v0.8.2 动效校准：时长只许来自 token，入场面板用 panel 档 ----

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"


def test_motion_durations_only_come_from_tokens():
    source = (STATIC / "motion-system.js").read_text(encoding="utf-8")

    for token in ("instant:90", "feedback:140", "enter:180", "panel:200", "exit:140"):
        assert token in source, f"缺运动时长 token：{token}"


def test_shell_styles_never_transition_all():
    import re

    offenders = []
    for name in ("index.html", "workbench-system.css"):
        text = (STATIC / name).read_text(encoding="utf-8")
        if re.search(r"transition\s*:\s*all", text):
            offenders.append(name)
    assert not offenders, f"还在用 transition:all（会连布局属性一起动）：{offenders}"


def test_dialog_entrance_uses_the_panel_duration(workbench):
    page, _ = workbench
    page.evaluate("FoxMotion.setPreference('system')")
    page.evaluate("window.FoxIntake.open()")
    durations = page.evaluate(
        """() => document.getAnimations()
             .map(a => (a.effect && a.effect.getTiming().duration) || 0)
             .filter(d => d > 0)""")

    assert any(abs(d - 200) < 1 for d in durations), f"面板入场应约 200ms，实测 {durations}"


def test_cards_transition_surface_not_geometry(workbench):
    page, _ = workbench
    props = page.eval_on_selector(".pal-card", "el => getComputedStyle(el).transitionProperty")

    assert "background" in props
    assert "transform" not in props, "卡片悬停不该位移：像素风靠面，不靠飘"
