"""v0.8.6 发版截图：手机预览二维码 + 一键交付包（真服务器 + 真实派发路径实拍）。

    evidence-phone-qr.png        顶栏 📱 → 手机预览弹窗（二维码 + 地址 + 警示）
    evidence-bundle-button.png   导出中心（分析完成、📦 一键交付包在场）
    evidence-bundle-result.png   组包完成（下载行 + 包内清单）

注：画布节点不接收 API 生成的项目（已知缺口），此处用 addNode 注入指向
真实项目的产物节点后，走 FoxActions.openExportCenter 派发——与按钮点击
同一条代码路径，弹窗/请求/结果全部真实。
"""
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_server_project_api import request as api_request  # noqa: E402

OUT = ROOT / "assets" / "screenshots" / "v0.8.6"
PROMPT = "做一个新品上市说明文档：轻巧保温杯，三色可选，续航 12 小时"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        payload, _ = api_request(server.base_url, "/api/generate", "POST",
                                 {"prompt": PROMPT, "intent": "doc",
                                  "quiet_llm": True})
        name = payload["project_name"]
        print(f"生成项目: {name}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.base_url)
            page.wait_for_function("typeof window.FoxActions === 'object'")

            # 一、手机预览：真实点击顶栏 📱（静态顶栏按钮，可直接点）
            page.click('[data-action="openPhonePreview"]')
            page.wait_for_selector("#phone-modal svg", timeout=15000)
            page.wait_for_selector("#phone-urls .menu-field", timeout=10000)
            page.wait_for_timeout(300)
            page.locator("#phone-modal").screenshot(
                path=OUT / "evidence-phone-qr.png")
            print("shot: evidence-phone-qr.png")
            page.click('[data-action="closePhonePreview"]')

            # 二、导出中心 + 📦：注入产物节点（指向真实项目），走真实派发路径
            page.evaluate(
                """name => {
                  const node = addNode('file', 120, 120, {
                    title: name, project_name: name,
                    project: 'output/' + name,
                    preview_url: '/output/' + name + '/output.html',
                    intent: 'doc', revision: 1});
                  window.FoxActions.openExportCenter(node.id);
                }""", name)
            page.wait_for_selector("#export-bundle", timeout=15000)
            page.wait_for_function(
                "document.querySelector('#export-status').textContent.includes('分析完成')",
                timeout=20000)
            page.wait_for_timeout(300)
            page.locator("#export-modal").screenshot(
                path=OUT / "evidence-bundle-button.png")
            print("shot: evidence-bundle-button.png")

            # 三、组包：点 📦 → 真实后台任务 → 结果行 + 包内清单
            page.click("#export-bundle")
            page.wait_for_function(
                "document.querySelector('#export-result').innerHTML.includes('bundle.zip')",
                timeout=120000)
            page.wait_for_timeout(300)
            page.locator("#export-modal").screenshot(
                path=OUT / "evidence-bundle-result.png")
            print("shot: evidence-bundle-result.png")
            browser.close()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
