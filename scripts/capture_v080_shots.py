"""Capture v0.8.0 evidence shots: the two feature views this release adds.

  1. export-centre-docx.png   — 导出中心，DOCX 选项对 doc 产物可见
  2. intake-blocks-preview.png — 审核台拆块预览（改写徽标 + 重新改写按钮）

Both are real product states driven through the product's own functions
(the same ones the C6 delegation table wires buttons to), against a real
server with a deterministic local rewriter. The five core workbench views
come from capture_core_shots.py against the same server; run that first
(or let this script's --core flag do it) so every card base carries the
v0.8.0 badge.

    python scripts/capture_v080_shots.py
"""
from __future__ import annotations

import hashlib
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import __version__, intake  # noqa: E402

PORT = 8638
BASE = f"http://127.0.0.1:{PORT}"
OUT = ROOT / "assets" / "screenshots" / f"v{__version__}"

PAGE = ("<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>狐构设计规范 · 参考页</title></head>\n<body><main>"
        "<section class=\"hero\"><h1>狐构 · 像素花园设计规范</h1>"
        "<p>这一页定义了狐构品牌的三个视觉支柱：暖纸底色、钴蓝主色、薄荷绿点缀，"
        "以及贯穿全部产物的圆角与留白尺度。</p></section>"
        "<section><h2>色彩系统</h2>"
        "<p>主色钴蓝 #173C8F 承担标题与主按钮；薄荷绿 #49B894 只用于点缀与"
        "成功态，不参与正文。陶土橙 #E57A3F 是唯一的强调色，每页至多出现一次。</p></section>"
        "<section><h2>排版与留白</h2>"
        "<p>正文使用系统衬线回退的 15 像素字号，行高 1.7；段间距固定为 14 像素，"
        "与卡片内边距共同构成呼吸感。</p></section>"
        "</main></body></html>")

REWRITES = {
    "这一页定义了狐构品牌的三个视觉支柱：暖纸底色、钴蓝主色、薄荷绿点缀，以及贯穿全部产物的圆角与留白尺度。":
        "狐构的视觉语言建立在三条支柱上：纸张般的暖色底、作为主色的钴蓝、点缀用的薄荷绿，"
        "再以统一的圆角与留白尺度贯穿所有产物。",
    "主色钴蓝 #173C8F 承担标题与主按钮；薄荷绿 #49B894 只用于点缀与成功态，不参与正文。陶土橙 #E57A3F 是唯一的强调色，每页至多出现一次。":
        "标题与主按钮交给钴蓝主色（#173C8F）；薄荷绿（#49B894）只出现在点缀与成功状态里；"
        "陶土橙（#E57A3F）作为唯一的强调色，每页最多登场一次。",
    "正文使用系统衬线回退的 15 像素字号，行高 1.7；段间距固定为 14 像素，与卡片内边距共同构成呼吸感。":
        "正文字号定在 15 像素并回退到系统衬线，行高 1.7；14 像素的固定段距和卡片内边距一起，"
        "撑起整个版面的呼吸感。",
}


def fake_rewriter(source, heading=""):
    return REWRITES.get(str(source).strip())


def inject_candidate(out_root: Path) -> str:
    body = PAGE.encode("utf-8")
    evidence = {
        "url": "https://example.com/hugoo-spec", "final_url": "https://example.com/hugoo-spec",
        "followed": ["https://example.com/hugoo-spec"], "status": 200,
        "content_type": "text/html; charset=utf-8", "body": body,
        "body_sha256": hashlib.sha256(body).hexdigest(), "body_bytes": len(body),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    source = {"id": "hugoo-demo", "name": "狐构演示源", "kind": "gallery",
              "license_class": "reference", "entry_url": "https://example.com/"}
    candidate = intake.extract_candidate(evidence, source=source)
    saved = intake.CandidateStore(out_root).save(candidate, evidence)
    intake.CandidateStore(out_root).set_status(saved["candidate_id"], "approved")
    return saved["candidate_id"]


def main() -> int:
    from htmlninefox.server import app as server_app

    out_root = ROOT / ".tmp" / "v080-shots-projects"
    out_root.mkdir(parents=True, exist_ok=True)
    server_app._OUTPUT_ROOT = out_root
    server_app._PARAPHRASE_REWRITER = fake_rewriter
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), server_app._Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    candidate_id = inject_candidate(out_root)
    print("approved candidate:", candidate_id)

    # 生成一个 doc 产物（离线引擎），导出中心才有真实的文字型产物可分析
    import json
    import urllib.request
    req = urllib.request.Request(
        BASE + "/api/generate",
        data=json.dumps({"prompt": "写一份「狐构像素花园设计系统」交付说明文档，"
                       "包含色彩、排版、组件三个章节", "intent": "doc",
                         "quiet_llm": True}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        gen = json.loads(resp.read().decode())
    print("generated:", gen.get("project"), "intent:", gen.get("intent"))
    project_name = Path(str(gen.get("project"))).name

    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    def clear_toasts(page):
        page.evaluate(
            "() => document.querySelectorAll('.fox-toast').forEach(t => t.remove())")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")
        assert page.inner_text("#ver").strip() == f"v{__version__}", "版本徽标不符"
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if page.evaluate("() => window.FoxActions && nodes.length >= 5"):
                    break
            except Exception:
                pass
            time.sleep(0.1)

        # ---- shot 1: 导出中心 · DOCX 选项（经 FoxExports.open 真实入口）----
        node_id = page.evaluate("""(projectName) => {
          const node = addNode('output', 430, 330, {
            title: '狐构像素花园设计系统 · 交付说明',
            project_name: projectName,
            revision: 0,
          });
          select(node);
          return node.id;
        }""", project_name)
        page.evaluate("id => window.FoxExports.open(id)", node_id)
        deadline = time.monotonic() + 45
        state = "missing"
        while time.monotonic() < deadline:
            state = page.evaluate(
                "() => { const o = document.querySelector('#export-format-docx');"
                " return o ? String(o.hidden) : 'missing'; }")
            if state == "false":
                break
            time.sleep(0.4)
        if state != "false":
            analysis = page.evaluate(
                "() => document.querySelector('#export-analysis').textContent")
            status = page.evaluate("() => document.querySelector('#export-status').textContent")
            raise SystemExit(
                f"DOCX 选项未解除隐藏（state={state}）· 状态栏={status} · 分析区={analysis[:160]}")
        page.select_option("#export-format", "docx")
        page.wait_for_timeout(600)
        clear_toasts(page)
        page.screenshot(path=str(OUT / "export-centre-docx.png"))
        print("  export-centre-docx.png",
              (OUT / "export-centre-docx.png").stat().st_size // 1024, "KB")
        page.evaluate("() => window.FoxExports.close()")

        # ---- shot 2: 审核台拆块预览（改写徽标 + 重新改写）----
        page.evaluate("() => window.FoxIntake.open()")
        page.wait_for_selector("#intake-modal", timeout=10000)
        page.evaluate("filter => window.FoxIntake.refresh(filter)", "approved")
        page.wait_for_timeout(900)
        button = page.locator(
            f'button[data-action="intakeShowBlocks"][data-id="{candidate_id}"]')
        assert button.count() == 1, "拆块预览按钮不存在"
        button.click()
        page.wait_for_selector(f"#intake-blocks-{candidate_id}:not([hidden])",
                               timeout=15000)
        page.wait_for_timeout(400)
        clear_toasts(page)
        # 把弹窗滚动到候选卡与面板可见的位置
        page.evaluate(
            """(cid) => {
              document.getElementById('intake-blocks-' + cid)
                .scrollIntoView({block: 'center'});
            }""", candidate_id)
        page.wait_for_timeout(300)
        clear_toasts(page)
        page.screenshot(path=str(OUT / "intake-blocks-preview.png"))
        print("  intake-blocks-preview.png",
              (OUT / "intake-blocks-preview.png").stat().st_size // 1024, "KB")

        # ---- shot 2b: 重改后的面板状态（"本次为重新改写"）----
        retry_button = page.locator(
            f'button[data-action="intakeRetryParaphrase"][data-id="{candidate_id}"]')
        assert retry_button.count() == 1, "重新改写按钮不存在"
        retry_button.click()
        page.wait_for_timeout(900)
        retried = page.evaluate(
            "(cid) => document.getElementById('intake-blocks-' + cid).textContent.includes('本次为重新改写')",
            candidate_id)
        assert retried, "重改后面板未显示「本次为重新改写」"
        clear_toasts(page)
        page.screenshot(path=str(OUT / "intake-blocks-retried.png"))
        print("  intake-blocks-retried.png",
              (OUT / "intake-blocks-retried.png").stat().st_size // 1024, "KB")
        page.evaluate("() => window.FoxIntake.close()")
        page.wait_for_timeout(500)

        # ---- shot 3: 生成的文档产物预览（真实 output 页面）----
        page.evaluate("id => window.openNodePreview(id)", node_id)
        page.wait_for_selector("#preview-modal", timeout=10000)
        page.wait_for_timeout(1200)
        clear_toasts(page)
        page.screenshot(path=str(OUT / "output-doc-preview.png"))
        print("  output-doc-preview.png",
              (OUT / "output-doc-preview.png").stat().st_size // 1024, "KB")
        browser.close()
    srv.shutdown()
    print("done →", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
