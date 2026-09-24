"""Browser gates for the Pixel Garden Workbench 2.0 convergence layer."""

from __future__ import annotations

from playwright.sync_api import sync_playwright


def _visible_overflow(page, selector: str) -> list[dict]:
    return page.eval_on_selector_all(
        selector,
        """elements => elements.filter(element => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 &&
            (rect.left < -1 || rect.right > innerWidth + 1);
        }).map(element => {
          const rect = element.getBoundingClientRect();
          return {id:element.id, text:(element.innerText || element.getAttribute('aria-label') || '').trim(), left:rect.left, right:rect.right};
        })""",
    )


def test_workbench_convergence_layout_icons_and_semantic_zoom(workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(server.base_url + "/")
        page.wait_for_function("window.FoxWorkbenchUI && document.querySelectorAll('.ui-icon svg').length > 20")

        assert page.locator("link[href='/workbench-system.css']").count() == 1
        assert page.locator(".ui-icon svg").count() > 20
        assert page.locator("#btn-create").evaluate("element => element.getBoundingClientRect().height") >= 36
        assert page.locator("#btn-go").get_attribute("aria-label") == "推进当前工作区"
        assert "推进当前工作区" in page.locator("#btn-go").inner_text()
        assert page.evaluate("document.querySelector('.topbar').scrollWidth <= document.querySelector('.topbar').clientWidth")
        assert not _visible_overflow(page, ".topbar-actions button,.topbar-tools > button,.topbar-more > summary")

        page.evaluate("camera.z=.7; applyCamera(false,false)")
        assert page.locator(".canvas-wrap").get_attribute("data-canvas-density") == "overview"
        assert page.locator("#node-2 .node-body").evaluate("element => getComputedStyle(element).display") == "none"
        page.evaluate("camera.z=1; applyCamera(false,false)")
        assert page.locator(".canvas-wrap").get_attribute("data-canvas-density") == "detail"
        assert page.locator("#node-2 .node-body").evaluate("element => getComputedStyle(element).display") != "none"

        page.set_viewport_size({"width": 768, "height": 1024})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not _visible_overflow(page, ".topbar-actions button,.topbar-tools > button,.topbar-more > summary")
        assert page.locator(".mobile-library-toggle").is_visible()
        assert page.locator(".mobile-inspector-toggle").is_visible()

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(220)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator('#mobile-task-view').is_visible()
        assert page.locator('.mobile-task-card').count() >= 1
        assert page.locator('.mobile-task-actions .btn').count() == 2
        assert page.locator('.mobile-library-toggle').evaluate("element => element.getBoundingClientRect().height") >= 40
        assert not _visible_overflow(page, ".topbar-actions button,.topbar-tools > button,.topbar-more > summary")
        bounds = page.locator("#motion-preference").bounding_box()
        assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390
        page.locator(".mobile-library-toggle").click()
        assert page.locator(".mobile-library-toggle").get_attribute("aria-expanded") == "true"
        assert page.locator("#sidebar").evaluate("element => element.classList.contains('mobile-open')")
        page.locator("#mobile-scrim").click(position={"x": 380, "y": 200})
        assert page.locator(".mobile-library-toggle").get_attribute("aria-expanded") == "false"
        page.locator(".mobile-task-card").first.click()
        assert page.locator(".mobile-inspector-toggle").get_attribute("aria-expanded") == "true"
        assert page.locator("#inspector").evaluate("element => element.classList.contains('mobile-open')")
        assert page.locator("#inspector").inner_text().strip() != "检查器"
        assert not errors
        browser.close()


def test_classic_mode_uses_pixel_garden_brand_tokens(workbench_server):
    with workbench_server as server, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(server.base_url + "/classic")
        assert page.title() == "Html九尾狐 · 经典表单模式"
        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(244, 240, 231)"
        assert page.evaluate("getComputedStyle(document.querySelector('#go')).backgroundColor") == "rgb(23, 60, 143)"
        assert page.locator("header.top img[src='/logo-mark.svg']").count() == 1
        page.locator("#prompt").focus()
        assert page.locator("#prompt").evaluate("element => getComputedStyle(element).outlineStyle") == "solid"
        browser.close()
