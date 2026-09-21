"""Browser coverage for the v0.5 interaction system."""

from __future__ import annotations


from playwright.sync_api import sync_playwright



def test_interaction_feedback_commands_and_dialog_focus(tmp_path, workbench_server):
    with workbench_server as server:
        base = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.clear()")
            page.goto(base + "/")
            page.wait_for_function(
                "window.FoxInteraction && window.FoxCanvasProductivity && document.querySelectorAll('.node').length >= 4",
                timeout=15000,
            )

            assert page.locator("#toast-region").get_attribute("role") == "status"
            assert page.locator("#toast-region").get_attribute("aria-live") == "polite"
            page.evaluate("flash('交互系统反馈测试', true)")
            assert page.locator("#tl-status").inner_text() == "交互系统反馈测试"
            toast = page.locator("#toast-region .fox-toast").filter(has_text="交互系统反馈测试")
            assert toast.count() == 1
            assert toast.get_attribute("data-toast-type") == "success"

            original_label = page.locator("#btn-create").inner_text()
            page.evaluate("FoxInteraction.setBusy('#btn-create', true, '处理中…')")
            assert page.locator("#btn-create").is_disabled()
            assert page.locator("#btn-create").get_attribute("aria-busy") == "true"
            assert page.locator("#btn-create").inner_text() == "处理中…"
            page.evaluate("FoxInteraction.setBusy('#btn-create', false)")
            assert not page.locator("#btn-create").is_disabled()
            assert page.locator("#btn-create").inner_text() == original_label

            page.locator("#btn-create").click()
            page.wait_for_function("document.activeElement?.id === 'creation-prompt'")
            page.keyboard.press("Escape")
            page.wait_for_function("document.querySelector('#create-modal').hidden && document.activeElement?.id === 'btn-create'")

            theme_before = page.evaluate("document.documentElement.dataset.theme")
            page.keyboard.press("Control+K")
            page.wait_for_selector("#canvas-command:not([hidden])")
            assert page.locator(".command-section-label", has_text="操作").count() == 1
            assert page.locator(".command-section-label", has_text="节点").count() == 1
            page.fill("#canvas-command-input", "切换主题")
            page.locator("#canvas-command-input").press("ArrowDown")
            page.locator("#canvas-command-input").press("Enter")
            page.wait_for_function("document.querySelector('#canvas-command').hidden")
            assert page.evaluate("document.documentElement.dataset.theme") != theme_before

            node_id = page.evaluate("""() => {
                const ws = activeWorkspace();
                const node = addNode('note', ws.x + 560, ws.y + 160, {
                    title:'交互系统唯一节点', workspaceId:ws.id,
                });
                FoxCanvasProductivity.commitHistory();
                return node.id;
            }""")
            page.keyboard.press("Control+K")
            page.fill("#canvas-command-input", "交互系统唯一节点")
            page.locator(f'[data-canvas-result="{node_id}"]').click()
            assert page.evaluate("selected") == node_id
            assert page.locator("#canvas-command").is_hidden()

            page.keyboard.press("Control+K")
            page.fill("#canvas-command-input", "打开 AI 模型配置")
            page.locator("#canvas-command-input").press("Enter")
            page.wait_for_function("document.activeElement?.id === 'ai-enabled'")
            page.keyboard.press("Escape")
            page.wait_for_function("document.querySelector('#ai-modal').hidden && document.activeElement?.id === 'btn-ai-settings'")

            assert not errors
            browser.close()
